#!/usr/bin/env python3
import logging

from pywot.rules import (
    Rule,
    run_main,
)
from pywot.rule_triggers import (
    AbsoluteTimeTrigger
)


class MorningWakeRule(Rule):

    def register_triggers(self):
        morning_wake_trigger = AbsoluteTimeTrigger("morning_wake_trigger", "06:30:00")
        return (morning_wake_trigger,)

    def action(self, *args):
        self.Bedside_Ikea_Light.on = True


def main(config, rule_system):
    my_rule = MorningWakeRule(rule_system, 'turn on bedside light at wake time')
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
