#!/usr/bin/env python3

"""This Web Thing implements a monitor for the price of bitcoin.  The objective is to
turn change the state of a light to indicate an inflating or deflating price of bitcoin
by polling the conversion rate from coindesk.

Once the app is running, --help will give a complete listing of the options.  Alternatively,
running with the option --admin.dump_conf=my_config.ini  will create an ini file that then
can be edited to set the parameters.  Thereafter, running with --admin.conf=my_config.ini will
load configuration from the file.
"""

import aiohttp
import async_timeout
import json
import logging

from configman import (
    configuration,
    Namespace,
    class_converter,
)

def create_url(config, local_namespace, args):
    """generate a URL to fetch tide data from Weather Underground using
    configuration data"""
    return "http://api.wunderground.com/api/{}/conditions/q/{}/{}.json".format(
        local_namespace.weather_underground_api_key,
        local_namespace.state_code,
        local_namespace.city_name
    )


del calc_tide_trend(current, previous):
    return 17   # TODO: make it real


class TideLight(WoTThing):
    required_config = Namespace()
    required_config.add_option(
        'name',
        doc='the name of this Tide Light',
        default="tide light",
    )
    required_config.add_option(
        'weather_underground_api_key',
        doc='the api key to access Weather Underground data',
        short_form="K",
        default="not a real key"
    )
    required_config.add_option(
        'tide_location',
        doc='the WU compatible tide location',
        default="something"
    )
    required_config.add_aggregation(
        'target_url',
        function=create_url
    )
    required_config.add_option(
        'light_url',
        doc='the Things Gateway URL for the light to control as the tide light',
        default="something"
    )
    required_config.add_option(
        'seconds_for_timeout',
        doc='the number of seconds to allow for fetching tide data',
        default=10
    )
    
    def __init__(self, config):
        super(TideLight, self).__init__(
            config,
            config.name,
            "thing",
            "my weather station with data for {}".format(config.tide_location)
        )
        self.previous_value = 0

    async def get_tide_info(self):
        async with aiohttp.ClientSession() as session:
            async with async_timeout.timeout(self.config.seconds_for_timeout):
                async with session.get(self.config.target_url) as response:
                    self.tide_info = json.loads(await response.text())
        current_observation = self.tide_info[...]  # TODO: 
        self.trend = self.calc_tide_trend(current_observation, self.previous_value)
        self.previous_value = current_observation
        logging.debug(
            'new value fetched: %s, trend: %s',
            current_observation,
            self.trend,
        )

    trend = WoTThing.wot_property(
        name='trend',
        initial_value=0,
        description='the trend positive or negative',
        value_source_fn=get_tide_info,
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
        name="tide_light_class",
        default=TideLight,
        doc="the fully qualified name of the bitcoin class",
        from_string_converter=class_converter
    )
    required_config.update(logging_config)
    config = configuration(required_config)

    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format
    )
    log_config(config)

    tide_monitor = config.bit_coin_class(config)

    server = config.server.wot_server_class(
        config,
        [tide_monitor],
        port=config.server.service_port
    )
    server.run()
    logging.debug('done.')
