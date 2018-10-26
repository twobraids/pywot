#!/usr/bin/env python3
import logging

from datetime import (
    datetime,
    timedelta
)

from pywot.rules import (
    Rule,
    run_main,
)
from pywot.rule_triggers import (
    DelayTimer,
)

class CombinationLightRule(Rule):

    def initial_state(self):
        self.index = 0
        self.combinations = [
            (False, False, False),
            (True, False, False),
            (True, True, False),
            (True, True, True),
            (False, True, True),
            (False, False, True),
            (False, True, False),
            (True, False, True),
        ]

    def register_triggers(self):
        self.KitchenButton.subscribe_to_event('pressed')
        self.KitchenButton.subscribe_to_event('longPressed')
        return (self.KitchenButton, )

    def set_bulb_state(self):
        self.StoveLight.on = self.combinations[self.index][0]
        self.CounterLight.on = self.combinations[self.index][1]
        self.SinkLight.on = self.combinations[self.index][2]

    def action(self, the_triggering_thing, the_trigger_event, new_value):
        if the_trigger_event == "pressed":
            self.index = (self.index + 1) % len(self.combinations)
            self.set_bulb_state()

        elif the_trigger_event == "longPressed":
            self.index = 0
            self.set_bulb_state()


def main(config, rule_system):
    my_rule = CombinationLightRule(
        config,
        rule_system,
        'combination light rule'
    )
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
