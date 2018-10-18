#!/usr/bin/env python3
import logging

from pywot.rules import (
    Rule,
    run_main,
)
from pywot.rule_triggers import (
    DurationTimer
)


class DurationRule(Rule):
    def register_triggers(self):
        return (
            self.Philips_HUE_01,
            DurationTimer(self.config, "ten_second_timer", "10s")
        )

    def action(self, the_changed_thing, the_changed_property, the_new_value):
        if the_changed_thing is self.Philips_HUE_01:
            state = (self.ten_second_timer.is_running, the_changed_property, the_new_value)
            if state == (False, 'on', True):
                # start the timer when the light turns on
                self.ten_second_timer.start_timer()
            elif state == (True, 'on', False):
                # cancel the timer if the light gets turned off
                self.ten_second_timer.cancel()

        elif the_changed_thing is self.ten_second_timer:
            self.Philips_HUE_01.on = the_new_value


def main(config, rule_system):
    my_rule = DurationRule(
        config,
        rule_system,
        'if bulb 01 is turned on then turn it off ten seconds later'
    )
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
