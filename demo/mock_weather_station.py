#!/usr/bin/env python3

import logging
from pywot import (
    WoTThing,
    logging_config,
    log_config
)
from configman import (
    configuration,
    Namespace,
    class_converter
)
from random import (
    randint,
    seed
)


class WeatherStation(WoTThing):
    def __init__(self, config):
        super(WeatherStation, self).__init__(
            config,
            "my weatherstation",
            "thing",
            "my weather station"
        )
        # initialize the weather station
        seed(100)

    async def get_weather_data(self):
        # do whatever it takes to get current temperature, pressure and wind speed
        self.temperature = randint(40, 80)
        self.barometic_pressure = randint(290, 310) / 10.0
        self.wind_speed = randint(0, 25)
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
        units='℉'
    )
    barometric_pressure = WoTThing.wot_property(
        name='barometric_pressure',
        initial_value=30.0,
        description='the air pressure in inches',
        units='in'
    )
    wind_speed = WoTThing.wot_property(
        name='wind_speed',
        initial_value=30.0,
        description='the wind speed in mph',
        units='mph'
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
    logging.debug('done.')
