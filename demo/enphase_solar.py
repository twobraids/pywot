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
import logging

from bs4 import BeautifulSoup

from pywot import (
    WoTThing,
    logging_config,
    log_config
)
from configman import (
    configuration,
    Namespace,
    class_converter,
)


def create_url(config, local_namespace, args):
    """the local network address URL for the Enphase Energy System """
    return "http://{}/home".format(
        config.enphase_address,
    )


class EnphaseEnergyMonitor(WoTThing):
    required_config = Namespace()
    required_config.add_option(
        'enphase_address',
        doc='local area network address ',
        default="10.0.0.101",
    )
    required_config.add_aggregation(
        'target_url',
        function=create_url
    )
    required_config.add_option(
        'seconds_for_timeout',
        doc='the number of seconds to allow for fetching enphase data',
        default=10
    )

    _LIFETIME_GENERATION = 1
    _CURRENTLY_GENERATING = 3
    _MICROINVERTER_TOTAL = 7
    _MICROINVERTERS_ONLINE = 9

    def __init__(self, config):
        super(EnphaseEnergyMonitor, self).__init__(
            config,
            "Enphase Solar Panels",
            "thing",
            "Data for my solar panels"
        )

    _multiplicative_factor = {
        'Wh': 0.001,
        'W': 0.001,
        'kWh': 1.0,
        'kW': 1.0,
        'MWh': 1000.0,
        'GWh': 1000000.0
    }

    @staticmethod
    def _scale_based_on_units(raw_string):
        number_as_str, units = raw_string.split()
        return float(number_as_str) * EnphaseEnergyMonitor._multiplicative_factor[units.strip()]

    async def get_enphase_data(self):
        async with aiohttp.ClientSession() as session:
            async with async_timeout.timeout(config.seconds_for_timeout):
                async with session.get(config.target_url) as response:
                    enphase_home_page_raw = await response.text()
        enphase_page = BeautifulSoup(enphase_home_page_raw, 'html.parser')
        # this is stupidly fragile - we're assuming this page format never
        # changes from fetch to fetch - observation has shown this to be ok
        # but don't know if that will hold over Enphase software updates.
        td_elements = enphase_page.find_all('table')[2].find_all('td')
        self.lifetime_generation = self._scale_based_on_units(
            td_elements[self._LIFETIME_GENERATION].contents[0]
        )
        self.generating_now = self._scale_based_on_units(
            td_elements[self._CURRENTLY_GENERATING].contents[0]
        )
        self.microinverter_total = td_elements[self._MICROINVERTER_TOTAL].contents[0]
        self.microinverters_online = td_elements[self._MICROINVERTERS_ONLINE].contents[0]
        logging.debug(
            'new values fetched: %s, %s, %s, %s',
            self.lifetime_generation,
            self.generating_now,
            self.microinverter_total,
            self.microinverters_online
        )

    lifetime_generation = WoTThing.wot_property(
        name='lifetime_generation',
        initial_value=0.0,
        description='Total lifetime generation in KWh',
        value_source_fn=get_enphase_data,
        units='KWh'
    )
    generating_now = WoTThing.wot_property(
        name='generating_now',
        initial_value=0.0,
        description='currently generating in KWh',
        units='KW'
    )
    microinverter_total = WoTThing.wot_property(
        name='microinverter_total',
        initial_value=0,
        description='the number of microinverters installed'
    )
    microinverters_online = WoTThing.wot_property(
        name='microinverters_online',
        initial_value=0,
        description='the number of micro inverters online',
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
        name="solar_panel_monitoring_class",
        default=EnphaseEnergyMonitor,
        doc="the fully qualified name of the class that monitors the solar panels",
        from_string_converter=class_converter
    )
    required_config.update(logging_config)
    config = configuration(required_config)

    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format
    )
    log_config(config)

    solar_panel_monitor = config.solar_panel_monitoring_class(config)

    server = config.server.wot_server_class(
        config,
        [solar_panel_monitor],
        port=config.server.service_port
    )
    server.run()
    logging.debug('done.')
