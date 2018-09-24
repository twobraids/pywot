#!/usr/bin/env python3
import logging


from pywot.rules import (
    Rule,
    run_main,
)


class FollowRule(Rule):

    def register_triggers(self):
        return ('Philips HUE 01', 'Philips HUE 02', 'Philips HUE 03', 'Philips HUE 04',)

    def action(self, a_thing, a_property, a_value):
        setattr(self.Philips_HUE_01, a_property, a_value)
        setattr(self.Philips_HUE_02, a_property, a_value)
        setattr(self.Philips_HUE_03, a_property, a_value)
        setattr(self.Philips_HUE_04, a_property, a_value)


def main(config, rule_system):
    my_rule = FollowRule(rule_system, '01 controls 02 03 04')
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
