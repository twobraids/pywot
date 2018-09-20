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
    TimeDevice
)

from follow_everything_rule import FollowRule


class TimedRule(Rule):

    def register_triggers(self):
        my_timer = TimeDevice( "my_timer", "09:46:00", '1s', '2s', 10)
        return (my_timer,)

    def action(self, *args):
        if self.my_timer.activated:
            self.Philips_HUE_02.on = True
        else:
            self.Philips_HUE_02.on = False

def main(config, rule_system):
    my_rule = TimedRule(rule_system, 'flash 10 times')
    rule_system.add_rule(my_rule)
    my_rule = FollowRule(rule_system, '01 controls 02 03 04')
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
