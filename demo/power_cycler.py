#!/usr/bin/python3

from webthing import (
    Event,
    Thing,
    WebThingServer
)
from asyncio import (
    Task,
    CancelledError,
    sleep,
    gather
)
from tornado.ioloop import (
    IOLoop
)
from aiohttp import (
    ClientSession
)
from async_timeout import (
    timeout
)
from configman import (
    configuration,
    Namespace
)
from collections import (
    Mapping
)
import logging


required_config = Namespace()
required_config.add_option(
    'service_port',
    doc='a port number for the Web Things Service',
    default=8888
)
required_config.add_option(
    'target_url',
    doc='a url outside the local network to determine if the router is up',
    default='http://uncommonrose.com'
)
required_config.add_option(
    'seconds_for_timeout',
    doc='the number of seconds to allow before assuming the router is down',
    default=10
)
required_config.add_option(
    'seconds_between_tests',
    doc='the number of seconds between each test trial',
    default=120
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


class RouterDownEvent(Event):
    def __init__(self, thing, data):
        super(RouterDownEvent, self).__init__(thing, 'router_down', data=data)


class RestartRouterEvent(Event):
    def __init__(self, thing, data):
        super(RestartRouterEvent, self).__init__(thing, 'restart_router', data=data)


class RouterPowerCycler(Thing):
    def __init__(self, config):
        self.config = config
        super(RouterPowerCycler, self).__init__(
            name='router_power_cycler',
            description='a Linux service as a Web Thing'
        )
        self.add_available_event(
            "router_down",
            {
                "description": "the router is down",
                "type": "boolean"
            }
        )
        self.add_available_event(
            "restart_router",
            {
                "description": "the router should restart",
                "type": "boolean"
            }
        )

        self.router_up = True

    async def hit_target_url(self):
        logging.debug('executing hit_target_url')
        try:
            async with ClientSession() as session:
                async with timeout(config.seconds_for_timeout):
                    async with session.get(config.target_url) as response:
                        # we're just awaitng a response before a timeout
                        # we don't really care what the response is
                        await response.text()
        except CancelledError as e:
            logging.debug('hit_target_url shutdown')
            raise e
        except Exception:
            logging.debug('target error')
            self.router_up = False

    async def monitor_router(self):
        while True:
            await self.hit_target_url()
            if self.router_up:
                logging.debug('sleep between tests for %s seconds', config.seconds_between_tests)
                await sleep(config.seconds_between_tests)
                continue
            logging.debug('add TargetDown')
            self.add_event(RouterDownEvent(self, True))
            logging.debug('leave service off for %s seconds', config.seconds_to_leave_router_off)
            await sleep(config.seconds_to_leave_router_off)
            logging.debug('add RestartTarget')
            self.add_event(RestartRouterEvent(self, True))
            logging.debug(
                'allow time for service to restart for %s seconds',
                config.seconds_to_restore_router
            )
            await sleep(config.seconds_to_restore_router)
            self.router_up = True


def log_config(config, prefix=''):
    for key, value in config.items():
        if isinstance(value, Mapping):
            log_config(value, "{}.".format(key))
        else:
            logging.info('%s%s: %s', prefix, key, value)


def run_server(config):
    logging.debug('run server')

    router_power_cycler = RouterPowerCycler(config)

    server = WebThingServer([router_power_cycler], port=config.service_port)
    try:
        # the Tornado Web server uses an asyncio event loop.  We want to
        # add tasks to that event loop, so we must reach into Tornado to get it
        io_loop = IOLoop.current().asyncio_loop
        logging.debug('create task')
        io_loop.create_task(router_power_cycler.monitor_router())
        logging.debug('server.start')
        server.start()

    except KeyboardInterrupt:
        logging.debug('stop signal received')
        # when stopping the server, we need to halt any tasks pending from the
        # method 'monitor_router'. Gather them together and cancel them en masse.
        pending_tasks_in_a_group = gather(*Task.all_tasks(), return_exceptions=True)
        pending_tasks_in_a_group.cancel()
        # let the io_loop run until the all the tasks complete their cancelation
        io_loop.run_until_complete(pending_tasks_in_a_group)
        # finally stop the server
        server.stop()


if __name__ == '__main__':
    config = configuration(required_config)
    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format
    )
    log_config(config)
    run_server(config)
