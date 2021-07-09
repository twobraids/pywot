#!/usr/bin/env python3

import logging
import random
import asyncio


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


class LampHardware:
    def __init__(self):
        self._on = False  # True = on; False = off
        self._level = 0  # 0% through 100%

    def get_lamp_state(self):
        return self._on

    def set_lamp_state(self, boolean_value):
        logging.debug('setting lamp to %s', bool(boolean_value))
        self._on = bool(boolean_value)

    def get_lamp_level(self):
        return self._level

    def set_lamp_level(self, value):
        if not (0 <= value <= 100):
            raise ValueError(
                'level must be between 0 and 100 - {} is #fail'.format(value)
            )
        logging.debug('setting the level: %s', value)
        self._level = value


class ExampleDimmableLight(WoTThing):

    def __init__(self, config, lamp_hardware):
        super(ExampleDimmableLight, self).__init__(
            config,
            'My Lamp',
            'dimmableLight',
            'A web connected lamp'
        )
        self._lamp_hardware = lamp_hardware

    async def _get_illumination_state(self):
        """this method will be run at a configurable interval to poll for changes of state
        of the lamp.  For example, to detect if a meddlesome child were to be randomly
        turning the light on/off and adjusting the brightness independently of this
        program."""
        self.on = self._lamp_hardware.get_lamp_state()
        self.level = self._lamp_hardware.get_lamp_level()

    def _set_hardware_illumination_state(self, boolean_value):
        # do whatever it takes to set the state of the lamp by
        # talking to the hardware
        self._lamp_hardware.set_lamp_state(boolean_value)

    def _set_hardware_level(self, new_level):
        # do whatever it takes to change the level of the lamp by
        # talking to the hardware
        self._lamp_hardware.set_lamp_level(new_level)

    on = WoTThing.wot_property(
        name='on',
        initial_value=True,
        description="is the light illuminated?",
        value_source_fn=_get_illumination_state,
        value_forwarder=_set_hardware_illumination_state
    )
    level = WoTThing.wot_property(
        name='level',
        initial_value=0,
        description="lamp brightness level",
        value_forwarder=_set_hardware_level,
        minimum=0,
        maximum=100
    )


class MeddlesomeChild:
    """a chaos monkey that will randomly change the state of the lamp hardware by
    directly manipulating it - not through the Things Gateway."""

    def __init__(self, lamp_hardware):
        self._lamp_hardware = lamp_hardware
        self.chaos_task = asyncio.get_event_loop().create_task(
            self.change_lamp_state_task()
        )

    async def change_lamp_state_task(self):
        logging.debug('change_lamp_state_task starting')
        while True:
            try:
                wait_time_in_seconds = random.randint(5, 30)
                logging.debug('meddlesome_child will act in %s seconds', wait_time_in_seconds)
                await asyncio.sleep(wait_time_in_seconds)
                if random.random() < 0.5:
                    logging.info('meddlesome child toggles the light')
                    self._lamp_hardware.set_lamp_state(
                        not self._lamp_hardware.get_lamp_state()
                    )
                else:
                    new_level = random.randint(0, 100)
                    if not self._lamp_hardware.get_lamp_state():
                        logging.info('meddlesome child turns the light on')
                        self._lamp_hardware.set_lamp_state(True)
                    logging.info('meddlesome child changes the dimmer to: %s', new_level)
                    self._lamp_hardware.set_lamp_level(new_level)
            except asyncio.CancelledError:
                break


if __name__ == '__main__':
    required_config = Namespace()
    required_config.server = Namespace()
    required_config.server.update(WoTServer.get_required_config())
    required_config.update(ExampleDimmableLight.get_required_config())
    required_config.seconds_between_polling.default = 1
    required_config.update(logging_config)
    config = configuration(required_config)
    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format
    )
    log_config(config)

    lamp_hardware = LampHardware()
    my_controllable_lamp = ExampleDimmableLight(config, lamp_hardware)

    meddlesome_child = MeddlesomeChild(lamp_hardware)

    server = WoTServer(
        config,
        [my_controllable_lamp],
        port=config.server.service_port
    )
    server.add_task(meddlesome_child.chaos_task)
    server.run()
    logging.debug('done.')
