#!/usr/bin/env python3
import logging

from pywot.rules import Rule


class ExampleWhileRule(Rule):

    def register_triggers(self):
        return (self.Philips_HUE_01,)

    def action(self, the_triggering_thing, the_changed_property_name, the_new_value):
        if the_changed_property_name == 'on':
            self.Philips_HUE_02.on = the_new_value
            self.Philips_HUE_03.on = the_new_value
            self.Philips_HUE_04.on = the_new_value


def main(config, rule_system):
    my_rule = ExampleWhileRule(rule_system, 'while 01 is on, turn on the others')
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    from pywot.rules import run_main

    run_main(main)

    logging.debug('done.')
