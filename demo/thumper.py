#!/usr/bin/env python3

"""This web thing a properity that cycles back and forth between
True and False for a configurable number of seconds. It is useful
for testing Things Gateway rules."""

from pywot import (
    WoTThing,
    WoTServer,
    logging_config,
    log_config
)
from configmanners import (
    configuration,
    Namespace,
)
import logging


class Thumper(WoTThing):
    def __init__(self, config):
        super(Thumper, self).__init__(config, "the thumper", "thing", "a thumper")

    async def get_next_value(self):
        self.thump = not self.thump
        logging.debug('fetched new value: %s', self.thump)

    thump = WoTThing.wot_property(
        name='thump',
        initial_value=True,
        description='thump',
        value_source_fn=get_next_value,
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
    required_config.server.update(WoTServer.get_required_config())
    required_config.update(Thumper.get_required_config())
    required_config.seconds_between_polling.default = 10
    required_config.update(logging_config)
    config = configuration(required_config)
    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format
    )
    log_config(config)

    thumper = Thumper(config)

    server = WoTServer(config, [thumper], port=config.server.service_port)
    server.run()
