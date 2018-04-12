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
import logging


class Thumper(WoTThing):
    def __init__(
        self,
        config,
        name='the thumper',
        type_='thing',
        description='a thumper'
    ):
        super(Thumper, self).__init__(config, name, type_, description)

    async def get_next_values(self):
        self.thump1 = int(not self.thump1)
        self.thump2 = int(not self.thump2) * 2
        self.thump3 = int(not self.thump3) * 3
        logging.debug('fetched new values: %s, %s, %s', self.thump1, self.thump2, self.thump3)

    thump1 = WoTThing.wot_property(
        name='thump1',
        initial_value=0,
        description='thump1',
        value_source_fn=get_next_values,
    )
    thump2 = WoTThing.wot_property(
        name='thump2',
        initial_value=0,
        description='thump2',
    )
    thump3 = WoTThing.wot_property(
        name='thump3',
        initial_value=0,
        description='thump3',
    )


def run_server(config):
    logging.debug('run server')

    thumper = config.thumper_class(config)

    server = config.server.wot_server_class(
        config,
        [thumper],
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
        name="thumper_class",
        default=Thumper,
        doc="the fully qualified name of the Thumper class",
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
    config = configuration(required_config)
    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format
    )
    log_config(config)

    run_server(config)
