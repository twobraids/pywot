#!/usr/bin/env python3
import logging

from datetime import (
    datetime,
    time
)

from pywot.rules import (
    Rule,
    run_main,
)
from pywot.rule_triggers import (
    AbsoluteTimeTrigger
)


class AbsoluteTimeRule(Rule):

    def register_triggers(self):
        my_timer = AbsoluteTimeTrigger( "my_timer", "12:18:00")
        return (my_timer,)

    def action(self, *args):
        if self.my_timer.activated:
            self.Philips_HUE_02.on = True

def main(config, rule_system):
    my_rule = AbsoluteTimeRule(rule_system, 'turn on at 12:00 every day')
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
