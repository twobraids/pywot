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

import aiohttp
import async_timeout
import json
import logging

from pywot import (
    create_new_WoTThing_class,
    logging_config,
    log_config
)
from configman import (
    configuration,
    Namespace,
    class_converter,
)

WoTThing = create_new_WoTThing_class()
class BitcoinTrend(WoTThing):
    required_config = Namespace()
    required_config.add_option(
        'name',
        doc='the name of this Bitcoin Trend Monitor',
        default="bitcoin trend",
    )
    required_config.add_option(
        'target_url',
        doc='the URL for json data',
        default="https://api.coindesk.com/v1/bpi/currentprice/USD.json"
    )
    required_config.add_option(
        'seconds_for_timeout',
        doc='the number of seconds to allow for fetching bitcoin data',
        default=10
    )

    @staticmethod
    def sign(x):
        if x < 0:
            return -1
        if x > 0:
            return 1
        return 0

    def __init__(self, config):
        super(BitcoinTrend, self).__init__(
            config,
            config.name,
            "thing",
            "my bitcoin trend monitor"
        )
        self.previous_value = 0

    async def get_bitcoin_value(self):
        async with aiohttp.ClientSession() as session:
            async with async_timeout.timeout(self.config.seconds_for_timeout):
                async with session.get(self.config.target_url) as response:
                    self.bitcoin_data = json.loads(await response.text())
        current_observation = self.bitcoin_data['bpi']['USD']['rate_float']
        self.trend = self.sign(current_observation - self.previous_value)
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
        value_source_fn=get_bitcoin_value,
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
        name="bit_coin_class",
        default=BitcoinTrend,
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

    bit_coin_monitor = config.bit_coin_class(config)

    server = config.server.wot_server_class(
        config,
        [bit_coin_monitor],
        port=config.server.service_port
    )
    server.run()
    logging.debug('done.')
