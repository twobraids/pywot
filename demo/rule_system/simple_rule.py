#!/usr/bin/env python3
import logging


from pywot.rules import (
    Rule,
    run_main,
)


class SimpleRule(Rule):

    def register_triggers(self):
        return ('Philips HUE 01',)

    def action(self, *args):
        if self.Philips_HUE_01.on:
            self.Philips_HUE_02.on = True
            self.Philips_HUE_03.on = True
            self.Philips_HUE_04.on = True


def main(config, rule_system):
    my_rule = SimpleRule(rule_system, 'if bulb 01 is turned on, then turn on 02, 03 and 04')
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
