#!/usr/bin/env python3
import logging


from pywot.rules import (
    Rule,
    run_main,
)


class BondedThingsRule(Rule):
    def __init__(self, rule_system, name, *participating_things):
        super(BondedThingsRule, self).__init__(
            rule_system,
            name,
            *participating_things
        )

    def action(self, a_property_name, a_value):
        for a_thing in self.participating_things.values():
            setattr(a_thing, a_property_name, a_value)


def main(config, rule_system):
    my_rule = BondedThingsRule(
        rule_system,
        'bonded things',
        'Philips HUE 01',
        'Philips HUE 02',
        'Philips HUE 03',
        'Philips HUE 04'
    )
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
