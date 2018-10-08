#!/usr/bin/env python3
import logging

from pywot.rules import (
    Rule,
    run_main,
)
from pywot.rule_triggers import (
    AbsoluteTimeTrigger,
    DurationTimer
)


class AbsoluteAndDurationRule(Rule):

    def register_triggers(self):
        self.noon_trigger = AbsoluteTimeTrigger("ab_timer", "12:00:00")
        self.delay_timer = DurationTimer('delay_timer', "10m")
        return (self.noon_trigger, self.delay_timer)

    def action(self, the_changed_thing, the_changed_property, the_new_value):
        if the_changed_thing is self.noon_trigger:
            self.Philips_HUE_01.on = True
            self.delay_timer.start_timer()

        elif the_changed_thing is self.delay_timer:
            if the_changed_property == 'timer_status' and the_new_value is False:
                self.Philips_HUE_01.on = False


def main(config, rule_system):
    my_rule = AbsoluteAndDurationRule(
        rule_system,
        'if it is noon, turn on bulb 01 for ten minutes'
    )
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
