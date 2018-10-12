#!/usr/bin/env python3
import logging
import asyncio
from datetime import datetime

from pywot.rules import (
    Rule,
    run_main,
)
from pywot.rule_triggers import (
    AbsoluteTimeTrigger
)


class MorningWakeRule(Rule):

    @property
    def today_is_a_weekday(self):
        weekday = datetime.now().date().weekday()  # M0 T1 W2 T3 F4 S5 S6
        return weekday in range(5)

    @property
    def today_is_a_weekend_day(self):
        return not self.today_is_a_weekday

    def register_triggers(self):
        self.weekday_morning_wake_trigger = AbsoluteTimeTrigger(
            "weekday_morning_wake_trigger", "06:10:00"
        )
        self.weekend_morning_wake_trigger = AbsoluteTimeTrigger(
            "weekend_morning_wake_trigger", "07:10:00"
        )
        return (self.weekday_morning_wake_trigger, self.weekend_morning_wake_trigger)

    def action(self, the_changed_thing, *args):
        if the_changed_thing is self.weekday_morning_wake_trigger:
            if self.today_is_a_weekday:
                asyncio.ensure_future(self._off_to_full())
        elif the_changed_thing is self.weekend_morning_wake_trigger:
            if self.today_is_a_weekend_day:
                asyncio.ensure_future(self._off_to_full())

    async def _off_to_full(self):
        for i in range(20):
            new_level = (i + 1) * 5
            self.Bedside_Ikea_Light.on = True
            self.Bedside_Ikea_Light.level = new_level
            await asyncio.sleep(60)


def main(config, rule_system):
    my_rule = MorningWakeRule(rule_system, 'turn on bedside light at wake time')
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
