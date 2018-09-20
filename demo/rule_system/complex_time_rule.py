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
    AbsoluteTimeWithDurationTrigger
)


class ComplicatedTimeRule(Rule):

    def register_triggers(self):
        self.my_timer = AbsoluteTimeWithDurationTrigger("my_timer", "12:00:00", '1s', '2s', 20)
        return (self.my_timer, )

    def action(self, *args):
        if self.Philips_HUE_01.on and self.my_timer.activated:
            self.Philips_HUE_02.on = True
        else:
            self.Philips_HUE_02.on = False

def main(config, rule_system):
    my_rule = ComplicatedTimeRule(
        rule_system,
        'if bulb 01 is on and it is noon, then blink bulb 02 twenty times'
    )
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
