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


class TimedRule(Rule):
    def __init__(self, rule_system, name):
        self.my_timer = TimeDevice(rule_system.config, "my_timer", "17:02:00", '1s', '2s', 20)

        super(TimedRule, self).__init__(rule_system, name, 'Philips HUE 01', self.my_timer)

    def predicate(self, *args):
        logging.debug('predicate: %s %s', self.Philips_HUE_01.on, self.my_timer.triggered)
        return self.Philips_HUE_01.on and self.my_timer.triggered

    def action(self, *args):
        if self.my_timer.activated:
            self.Philips_HUE_02.on = True
        else:
            self.Philips_HUE_02.on = False

def main(config, rule_system):
    my_rule = TimedRule(rule_system, 'twenty_seconds')
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
