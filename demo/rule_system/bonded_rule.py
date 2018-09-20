#!/usr/bin/env python3
import logging

from pywot.rules import Rule


class BondedBulbsRule(Rule):

    def register_triggers(self):
        return (
            self.Philips_HUE_01,
            self.Philips_HUE_02,
            self.Philips_HUE_03,
            self.Philips_HUE_04,
        )

    def action(self, the_triggering_thing, the_changed_property_name, the_new_value):
        for a_thing in self.triggering_things.values():
            setattr(a_thing, the_changed_property_name, the_new_value)


def main(config, rule_system):
    my_rule = BondedBulbsRule(rule_system, 'bonded things')
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    from pywot.rules import run_main

    run_main(main)

    logging.debug('done.')
