#!/usr/bin/env python3
import logging

from pywot.rules import Rule


class ExampleIfRule(Rule):
    """This rule triggers on any change in state of the Philips_HUE_01 bulb.
    If that bulb was turned on then three other bulbs get turned on, too.
    If the trigger bulb was turned off, no action is taken.
    """

    def register_triggers(self):
        return (self.Philips_HUE_01,)

    def action(self, *args):
        if self.Philips_HUE_01.on:
            self.Philips_HUE_02.on = True
            self.Philips_HUE_03.on = True
            self.Philips_HUE_04.on = True


def main(config, rule_system):
    my_rule = ExampleIfRule(config, rule_system, 'if 01 turns on, turn on the others')
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    from pywot.rules import run_main

    run_main(main)

    logging.debug('done.')
