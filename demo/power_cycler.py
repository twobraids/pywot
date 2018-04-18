#!/usr/bin/env python3

import logging
from aiohttp import ClientSession
from async_timeout import timeout
from pywot import (
    WoTThing,
    WoTServer,
    logging_config,
    log_config
)
from asyncio import (
    CancelledError,
    sleep,
)
from configman import (
    configuration,
    Namespace
)


class RouterMonitor(WoTThing):
    required_config = Namespace()
    required_config.add_option(
        'target_url',
        doc='a url outside the local network to determine if the router is up',
        default='URL THAT DOES NOT MIND REPEATED HITS'
    )
    required_config.add_option(
        'seconds_for_timeout',
        doc='the number of seconds to allow before assuming the router is down',
        default=10
    )
    required_config.add_option(
        'seconds_to_leave_router_off',
        doc='the number of seconds to leave the router off after shutting it down',
        default=60
    )
    required_config.add_option(
        'seconds_to_restore_router',
        doc='the number of seconds required to power up the router',
        default=90
    )

    def __init__(self, config):
        super(RouterMonitor, self).__init__(
            config,
            "ComcastRouter",
            "thing",
            "a router that's a long way away"
        )

    async def is_the_router_ok(self):
        logging.debug('executing is_the_router_ok')
        try:
            async with ClientSession() as session:
                async with timeout(config.seconds_for_timeout):
                    async with session.get(config.target_url) as response:
                        # we're just awaitng a response before a timeout
                        # we don't really care what the response is
                        await response.text()
                        return True
        except CancelledError as e:
            logging.debug('is_the_router_ok shutdown')
            raise e
        except Exception as e:
            logging.debug("can't read external Website: {}".format(e))
            self.router_ok = False
            return False

    async def is_router_ok_polling_task(self):
        if not await self.is_the_router_ok():
            logging.debug('turn the router off for %s seconds', config.seconds_to_leave_router_off)
            await sleep(config.seconds_to_leave_router_off)
            self.router_ok = True
            logging.debug(
                'allow time for service to restart for %s seconds before testing begins again',
                config.seconds_to_restore_router
            )
            await sleep(config.seconds_to_restore_router)

    router_ok = WoTThing.wot_property(
        name="router_ok",
        initial_value=True,
        description="boolean value indication the state of the router",
        value_source_fn=is_router_ok_polling_task
    )


if __name__ == '__main__':
    required_config = Namespace()
    required_config.server = Namespace()
    required_config.server.update(WoTServer.get_required_config())
    required_config.update(RouterMonitor.get_required_config())
    required_config.update(logging_config)
    config = configuration(required_config)
    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format
    )
    log_config(config)

    router_power_cycler = RouterMonitor(config)
    server = WoTServer(config, [router_power_cycler], port=config.server.service_port)
    server.run()
