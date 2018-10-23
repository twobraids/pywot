#!/usr/bin/env python3
import logging
import asyncio

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

    def action(self, the_triggering_thing, *args):
        if the_triggering_thing is self.sunset_trigger:
            self.Philips_HUE_01.on = True
        else:
            self.Philips_HUE_01.on = False


class RahukaalamRule(Rule):

    def register_triggers(self):
        rahukaalam_trigger = DailySolarEventsTrigger(
            self.config,
            "rahukaalam_trigger",
            ("rahukaalam_start", "rahukaalam_end", ),
            (44.562951, -123.3535762),
            "US/Pacific",
            70.0,
            "-2250s"
        )
        return (rahukaalam_trigger,)

    async def blink(self, number_of_seconds):
        number_of_blinks = number_of_seconds / 3
        for i in range(int(number_of_blinks)):
            self.Philips_HUE_02.on = True
            await asyncio.sleep(2)
            self.Philips_HUE_02.on = False
            await asyncio.sleep(1)
        self.Philips_HUE_02.on = True

    def action(self, the_triggering_thing, the_trigger, *args):
        if the_trigger == "rahukaalam_start":
            logging.info('%s starts', self.name)
            self.Philips_HUE_02.on = True
            self.Philips_HUE_02.color = "#FF9900"
            asyncio.ensure_future(self.blink(30))
        else:
            logging.info('%s ends', self.name)
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
        'Rahukaalam warning light'
    )
    rule_system.add_rule(rahukaalam_warning_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
