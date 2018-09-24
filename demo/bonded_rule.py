#!/usr/bin/env python3
import logging


from pywot.rules import (
    Rule,
    run_main,
)


class BondedThingsRule(Rule):

    def register_triggers(self):
        return ('Philips HUE 01', 'Philips HUE 02', 'Philips HUE 03', 'Philips HUE 04')

    def action(self, the_changed_thing, the_changed_property_name, the_new_value):
        for a_thing in self.participating_things.values():
            setattr(a_thing, the_changed_property_name, the_new_value)


def main(config, rule_system):
    my_rule = BondedThingsRule(rule_system, 'bonded things')
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
