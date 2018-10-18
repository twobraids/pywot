#!/usr/bin/env python3
import logging

from datetime import (
    datetime,
    timedelta
)

from pywot.rules import (
    Rule,
    run_main,
)
from pywot.rule_triggers import (
    SunTrigger
)


class EveningPorchLightRule(Rule):

    def register_triggers(self):
        sun_trigger = SunTrigger(
            self.config,
            "sun_trigger",
            "sunset",
            (44.562951, -123.3535762),
            "US/Pacific",
            70.0,
            600  # ten minutes
        )
        return (sun_trigger,)

    def action(self, *args):
        self.FrontPorchLight.on = True

def main(config, rule_system):
    my_rule = EveningPorchLightRule(
        config,
        rule_system,
        'turn on front porch light ten minutes after sunset'
    )
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
