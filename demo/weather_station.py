#!/usr/bin/env python3

from pywot import (
    WoTThing,
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
import logging


class WeatherStation(WoTThing):
    def __init__(self, config, name='my_weatherstation', description='a weather station'):
        super(WeatherStation, self).__init__(config, name, description)
        # initialize the weather station
        seed(100)

    async def get_current_temperature(self):
        # do whatever it takes to get current temperature
        self.temperature = randint(40, 80)

    temperature = WoTThing.wot_property(
        name='temperature',
        initial_value=0,
        description='the temperature in F',
        value_source_fn=get_current_temperature,
    )

    async def get_current_pressure(self):
        # do whatever it takes to get current pressure
        self.pressure = randint(290, 310) / 10.0

    barometic_pressure = WoTThing.wot_property(
        name='barometric_pressure',
        initial_value=30,
        description='the air pressure in inches',
        value_source_fn=get_current_pressure,
    )


def run_server(config):
    logging.debug('run server')

    print(config.weather_station_class)
    weather_station = config.weather_station_class(config)

    server = config.server.wot_server_class(
        config,
        [weather_station],
        port=config.server.service_port
    )
    server.run()


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
    required_config.add_option(
        'logging_level',
        doc='log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)',
        default='DEBUG',
        from_string_converter=lambda s: getattr(logging, s.upper(), None)
    )
    required_config.add_option(
        'logging_format',
        doc='format string for logging',
        default='%(asctime)s %(filename)s:%(lineno)s %(levelname)s %(message)s',
    )
    print ('before configuration')
    config = configuration(required_config)
    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format
    )
    log_config(config)
    run_server(config)
