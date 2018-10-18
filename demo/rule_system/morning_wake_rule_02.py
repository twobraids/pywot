#!/usr/bin/env python3
import logging

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
            self.config, "weekday_morning_wake_trigger", "06:30:00"
        )
        self.weekend_morning_wake_trigger = AbsoluteTimeTrigger(
            self.config, "weekend_morning_wake_trigger", "07:30:00"
        )
        return (self.weekday_morning_wake_trigger, self.weekend_morning_wake_trigger)

    def action(self, the_changed_thing, *args):
        if the_changed_thing is self.weekday_morning_wake_trigger:
            if self.today_is_a_weekday:
                self.Bedside_Ikea_Light.on = True
        elif the_changed_thing is self.weekend_morning_wake_trigger:
            if self.today_is_a_weekend_day:
                self.Bedside_Ikea_Light.on = True


def main(config, rule_system):
    my_rule = MorningWakeRule(config, rule_system, 'turn on bedside light at wake time')
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
