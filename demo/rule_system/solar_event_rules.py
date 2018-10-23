#!/usr/bin/env python3
import logging

from pywot.rules import (
    Rule,
    run_main,
)
from pywot.rule_triggers import (
    DailySolarEventsTrigger,
    AbsoluteTimeTrigger
)


class EveningPorchLightRule(Rule):

    def register_triggers(self):
        self.sunset_trigger = DailySolarEventsTrigger(
            self.config,
            "sunset_trigger",
            ("sunset", ),
            (44.562951, -123.3535762),
            "US/Pacific",
            70.0,
            "10m"  # ten minutes
        )
        self.ten_pm_trigger = AbsoluteTimeTrigger(
            self.config,
            'ten_pm_trigger',
            '22:00:00'
        )
        return (self.sunset_trigger, self.ten_pm_trigger)

    def action(self, the_changed_thing, *args):
        if the_changed_thing is self.sunset_trigger:
            self.Philips_HUE_01.on = True
        else:
            self.Philips_HUE_01.on = False


class RahukaalamRule(Rule):

    def register_triggers(self):
        events_trigger = DailySolarEventsTrigger(
            self.config,
            "rahukaalam_trigger",
            ("rahukaalam_start", "rahukaalam_end", ),
            (44.562951, -123.3535762),
            "US/Pacific",
            70.0
        )
        return (events_trigger,)

    def action(self, the_changed_thing, the_changed_property, new_value):
        if new_value is True:
            self.Philips_HUE_02.on = True
            self.Philips_HUE_02.color = "#FF9900"
        else:
            self.Philips_HUE_02.on = False


def main(config, rule_system):
    evening_porch_rule = EveningPorchLightRule(
        config,
        rule_system,
        'turn on front porch light ten minutes after sunset'
    )
    rule_system.add_rule(evening_porch_rule)

    rahukaalam_warning_rule = RahukaalamRule(
        config,
        rule_system,
        'warning light during Rahukaalam'
    )
    rule_system.add_rule(rahukaalam_warning_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
