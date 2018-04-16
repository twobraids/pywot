#!/usr/bin/env python3

"""This Web Thing implements a virtual weather station using data from Weather Underground.
It exposes temperature, barometric pressure and wind speed in three properties that can be
used as the basis for rules in the Things Gateway.

To use this Web Thing, a developer API key must be acquired from Weather Underground at this URL:
https://www.wunderground.com/weather/api/d/pricing.html

I use the Developer version of the Cumulus Plan which allows for 500 API hits for a cost of 0$.
That translates to fetching weather data every three minutes.

Once the app is running, --help will give a complete listing of the options.  Alternatively,
running with the option --admin.dump_conf=my_config.ini  will create an ini file that then
can be edited to set the parameters.  Thereafter, running with --admin.conf=my_config.ini will
load configuration from the file.
"""

import asyncio
import aiohttp
import async_timeout
import json
import logging

from pywot import (
    WoTThing,
    logging_config,
    log_config
)
from configman import (
    configuration,
    Namespace,
    class_converter,
    RequiredConfig,
)


def create_url(config, local_namespace, args):
    """generate a URL to fetch local weather data from Weather Underground using
    configuration data"""
    return "http://api.wunderground.com/api/{}/conditions/q/{}/{}.json".format(
        config.weather_underground_api_key,
        config.state_code,
        config.city_name
    )


class WeatherStation(WoTThing, RequiredConfig):
    required_config = Namespace()
    required_config.add_option(
        'weather_underground_api_key',
        doc='the api key to access Weather Underground data',
        short_form="K",
        default="not a real key"
    )
    required_config.add_option(
        'state_code',
        doc='the two letter state code',
        default="OR",
    )
    required_config.add_option(
        'city_name',
        doc='the name of the city',
        default="Corvallis",
    )
    required_config.add_aggregation(
        'target_url',
        function=create_url
    )
    required_config.add_option(
        'seconds_for_timeout',
        doc='the number of seconds to allow for fetching weather data',
        default=10
    )

    def __init__(self, config):
        super(WeatherStation, self).__init__(
            config,
            "my weatherstation",
            "thing",
            "my weather station with data for {}, {}".format(config.city_name, config.state_code)
        )
        self.weather_data = {
            'current_observation': {
                'temp_f': self.temperature,
                'pressure_in': self.barometric_pressure,
                'wind_mph': self.wind_speed,
            }
        }

    async def get_weather_data(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(config.seconds_for_timeout):
                    async with session.get(config.target_url) as response:
                        self.weather_data = json.loads(await response.text())
        except Exception as e:
            logging.critical('loading weather data fails: %s', e)
            if isinstance(e, asyncio.CancelledError):
                # we want an app shutdown exception to propagate
                raise e
        self.temperature = self.weather_data['current_observation']['temp_f']
        self.barometric_pressure = self.weather_data['current_observation']['pressure_in']
        self.wind_speed = self.weather_data['current_observation']['wind_mph']
        logging.debug(
            'new values fetched: %s, %s, %s',
            self.temperature,
            self.barometric_pressure,
            self.wind_speed
        )

    temperature = WoTThing.wot_property(
        name='temperature',
        initial_value=0.0,
        description='the temperature in ℉',
        value_source_fn=get_weather_data,
        metadata={
            'units': '℉'
        }
    )
    barometric_pressure = WoTThing.wot_property(
        name='barometric_pressure',
        initial_value=30.0,
        description='the air pressure in inches',
        metadata={
            'units': 'in'
        }
    )
    wind_speed = WoTThing.wot_property(
        name='wind_speed',
        initial_value=30.0,
        description='the wind speed in mph',
        metadata={
            'units': 'mph'
        }
    )

if __name__ == '__main__':
    required_config = Namespace()
    required_config.server = Namespace()
    required_config.server.add_option(
        name='wot_server_class',
        default="pywot.WoTServer",
        doc="the fully qualified name of the WoT Server class",
        from_string_converter=class_converter
    )
    required_config.add_option(
        name="weather_station_class",
        default=WeatherStation,
        doc="the fully qualified name of the WoT weather station class",
        from_string_converter=class_converter
    )
    required_config.update(logging_config)
    config = configuration(required_config)

    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format
    )
    log_config(config)

    weather_station = config.weather_station_class(config)

    server = config.server.wot_server_class(
        config,
        [weather_station],
        port=config.server.service_port
    )
    server.run()
