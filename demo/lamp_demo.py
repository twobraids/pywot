#!/usr/bin/env python3

import logging

from pywot import (
    WoTThing,
    WoTServer,
    logging_config,
    log_config
)
from configman import (
    configuration,
    Namespace,
    class_converter,
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
        on = self._lamp_hardware.get_lamp_state()
        level = self._lamp_hardware.get_lamp_level()

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
        value_forwarder=_set_hardware_level
    )


if __name__ == '__main__':
    required_config = Namespace()
    required_config.server = Namespace()
    required_config.server.update(WoTServer.get_required_config())
    required_config.update(ExampleDimmableLight.get_required_config())
    print(list(required_config.keys()))
    required_config.seconds_between_polling.default = 10
    required_config.update(logging_config)
    config = configuration(required_config)
    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format
    )
    log_config(config)

    lamp_hardware = LampHardware()
    my_controllable_lamp = ExampleDimmableLight(config, lamp_hardware)

    server = WoTServer(
        config,
        [my_controllable_lamp],
        port=config.server.service_port
    )
    server.run()
    logging.debug('done.')



