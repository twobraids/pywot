#!/usr/bin/env python3
import logging
import asyncio

from datetime import (
    datetime,
    time
)

from pywot.rules import (
    Rule,
    run_main,
)
from pywot.rule_triggers import (
    TimeBasedTrigger
)


class DurationRule(Rule):
    def initial_state(self):
        self.duration = TimeBasedTrigger.duration_str_to_seconds("10s")

    def register_triggers(self):
        return ('Philips HUE 01',)

    def action(self, the_changed_thing, the_changed_property, the_new_value):
        if the_changed_property == 'on' and the_new_value is True:
            logging.debug(
                'Duration Rule: turning off %s in %s seconds' % (
                    the_changed_thing.name,
                    self.duration
                )
            )
            async def turn_off():
                await asyncio.sleep(self.duration)
                self.Philips_HUE_01.on = False
            asyncio.ensure_future(turn_off())

def main(config, rule_system):
    my_rule = DurationRule(
        rule_system,
        'if bulb 01 is turned on then turn it off ten seconds later'
    )
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
