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


class TimedRule(Rule):

    def register_triggers(self):
        self.my_timer = AbsoluteTimeTrigger("my_timer", "11:26:00", '1s', '2s', 20)
        return ('Philips HUE 01', self.my_timer)

    def action(self, *args):
        if self.Philips_HUE_01.on and self.my_timer.activated:
            self.Philips_HUE_02.on = True
        else:
            self.Philips_HUE_02.on = False

def main(config, rule_system):
    my_rule = TimedRule(rule_system, 'twenty_seconds')
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
