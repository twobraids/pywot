#!/usr/bin/env python3

# This is an example of using the Things Framework to make a custom controller
# to mediate between a thermostat and Quadrafire Santa Fe pellet stove in the
# volatile temperature environment of a yurt.

# Starting and stopping a pellet stove requires 350W of power for about five
# minutes during startup.  Thereafter, the electricity use is minimal as it just
# runs fans and the auger.

# The yurt is just a fancy tent that doesn't hold heat very well.  Using a
# standard thermostat during cold weather sets up a cycle of wildly fluctuating
# temperatures that rarely averages out to be the setting on the thermostat.
# When the thermostat turns off the pellet stove, the temperature in the yurt
# goes into freefall.  Even if the thermostat turns the stove back on again
# immediately, if the outdoor temperature is low, it might take the pellet
# stove thirty or forty minutes to recover the temperature.

# This program resolves the temperature volatility by not allowing the
# thermostat to abruptly turn off the stove.  When the thermostat
# turns off its "call signal", instead of shutting down, the stove just drops
# a level of intensity: going from high to medium.  If, after a configurable
# number of minutes passes, the thermostat hasn't called for more heat, the
# stove backs down another level to low.  The stove only shuts down after the
# low timer expires.  At anytime during the slow backing off shutdown the
# thermostat may turn the stove up to high.

# This smooths out the wild peaks and valleys of the temperature fluctuation.

# Future enhancements: adding a outdoor temperature monitor to adjust the length
# of the medium and low level timeouts.  This would fix the problem of overheating
# the yurt during mild weather.

import logging
import asyncio
import contextlib

from configman import (
    Namespace,
    configuration,
    class_converter
)

from pywot import (
    WoTThing,
    WoTServer,
    logging_config,
    log_config
)


class PelletStove(WoTThing):
    required_config = Namespace()
    required_config.add_option(
        name='startup_level',
        doc='the stove intensity level used on startup',
        default='high',  # low, medium, high
    )
    required_config.add_option(
        name='medium_linger_time_in_minutes',
        doc='the time in minutes of lingering on medium during shutdown',
        default=5.0,
    )
    required_config.add_option(
        name='low_linger_time_in_minutes',
        doc='the time in minutes of lingering on low during shutdown',
        default=5.0,
    )
    required_config.add_option(
        'controller_implementation_class',
        doc='a fully qualified name of a class that can control the stove',
        default='stove_controller.StoveControllerImplementation',
        from_string_converter=class_converter
    )

    def __init__(self, config):
        super(PelletStove, self).__init__(
            config,
            "Pellet Stove Controller",
            "thing",
            "pellet stove automation"
        )
        self.set_medium_linger(config.medium_linger_time_in_minutes)
        self.set_low_linger(config.low_linger_time_in_minutes)

        self._controller = config.controller_implementation_class()
        self.lingering_shutdown_task = None

        self.logging_count = 0

    async def get_thermostat_state(self):
        previous_thermostat_state = self.thermostat_state
        self.thermostat_state = self._controller.get_thermostat_state()
        self.logging_count += 1
        if self.logging_count % 300 == 0:
            logging.debug('still monitoring thermostat')
            self.logging_count = 0
        if previous_thermostat_state != self.thermostat_state:
            if self.thermostat_state:
                logging.info('start heating')
                await self.set_stove_mode_to_heating()
            else:
                logging.info('start lingering shutdown')
                self.lingering_shutdown_task = asyncio.get_event_loop().create_task(
                    self.set_stove_mode_to_lingering()
                )

    def set_medium_linger(self, value_in_minutes):
        self.medium_linger_time_in_seconds = value_in_minutes * 60
        logging.debug('medium_linger_time set to %s seconds',self.medium_linger_time_in_seconds)

    def set_low_linger(self, value_in_minutes):
        self.low_linger_time_in_seconds = value_in_minutes * 60
        logging.debug('low_linger_time set to %s seconds',self.low_linger_time_in_seconds)

    thermostat_state = WoTThing.wot_property(
        name='thermostat_state',
        description='the on/off state of the thermostat',
        initial_value=False,
        value_source_fn=get_thermostat_state,
    )
    stove_state = WoTThing.wot_property(
        name='stove_state',
        description='the stove intensity level',
        initial_value='off',  # off, low, medium, high
    )
    stove_automation_mode = WoTThing.wot_property(
        name='stove_automation_mode',
        description='the current operating mode of the stove',
        initial_value='off',  # off, heating, lingering_in_medium, lingering_in_low, overridden
    )
    medium_linger_minutes = WoTThing.wot_property(
        name='medium_linger_minutes',
        description='how long should the medium level last during lingering shutdown',
        initial_value=5.0,
        value_forwarder=set_medium_linger
    )
    low_linger_minutes = WoTThing.wot_property(
        name='low_linger_minutes',
        description='how long should the low level last during lingering shutdown',
        initial_value=5.0,
        value_forwarder=set_low_linger
    )

    async def set_stove_mode_to_heating(self):
        if self.lingering_shutdown_task:
            logging.debug('canceling lingering shutdown to turn stove back to high')
            self.lingering_shutdown_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.lingering_shutdown_task
            self.lingering_shutdown_task = None
        self._controller.set_on_high()
        self.stove_state = 'high'
        self.stove_automation_mode = 'heating'

    async def set_stove_mode_to_lingering(self):
        self._controller.set_on_medium()
        self.stove_state = 'medium'
        self.stove_automation_mode = 'lingering_in_medium'
        logging.debug(
            'stove set to medium for %s seconds',
            self.medium_linger_time_in_seconds
        )
        await asyncio.sleep(self.medium_linger_time_in_seconds)

        self._controller.set_on_low()
        self.stove_state = 'low'
        self.stove_automation_mode = 'lingering_in_low'
        logging.debug(
            'stove set to low for %s seconds',
            self.low_linger_time_in_seconds
        )
        await asyncio.sleep(self.low_linger_time_in_seconds)

        self._controller.set_off()
        self.stove_state = 'off'
        self.stove_automation_mode = 'off'
        logging.info('stove turned off')
        self.lingering_shutdown_task = None

    def shutdown(self):
        if self.lingering_shutdown_task:
            logging.debug('lingering_shutdown_task is pending - canceling')
            self.lingering_shutdown_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                asyncio.get_event_loop().run_until_complete(self.lingering_shutdown_task)
        self._controller.shutdown()


if __name__ == '__main__':
    required_config = Namespace()
    required_config.server = Namespace()
    required_config.server.update(WoTServer.get_required_config())
    required_config.update(PelletStove.get_required_config())
    required_config.seconds_between_polling.default = 1
    required_config.update(logging_config)
    config = configuration(required_config)
    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format
    )
    log_config(config)

    pellet_stove = PelletStove(config)

    server = WoTServer(
        config,
        [pellet_stove],
        port=config.server.service_port
    )
    server.run()

    pellet_stove.shutdown()

    logging.debug('done.')
