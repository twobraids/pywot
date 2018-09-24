#!/usr/bin/env python3
import logging


from pywot.rules import (
    Rule,
    run_main,
)


class FollowRule(Rule):

    def register_triggers(self):
        return ('Philips HUE 01',)

    def action(self, the_changed_thing, the_changed_property_name, the_new_value):
        if the_changed_property_name == 'on':
            self.Philips_HUE_02.on = the_new_value
            self.Philips_HUE_03.on = the_new_value
            self.Philips_HUE_04.on = the_new_value


def main(config, rule_system):
    my_rule = FollowRule(rule_system, '01 controls 02 03 04')
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
