#!/usr/bin/env python3
import logging

from sys import exit
from datetime import datetime

from pywot.rules import (
    Rule,
    run_main,
)
from pywot.rule_triggers import (
    HeartBeat,
    DelayTimer
)


class OzoneRule(Rule):

    def register_triggers(self):
        self.heartbeat = HeartBeat(self.config, 'the_heart', "20s")
        self.ozone_on_timer = DelayTimer(self.config, "ozone_on_timer", "5s")
        self.total_cycle_timer = DelayTimer(self.config, "total_cycle_timer", "2m")
        self.total_cycle_timer.add_time()
        self.end_of_cycle_timer = DelayTimer(self.config, "end_of_cycle_timer", "10s")
        return (self.heartbeat, self.ozone_on_timer, self.total_cycle_timer, self.end_of_cycle_timer)

    def action(self, the_trigger, the_event, new_value):
        logging.debug('OzoneRule action %s %s %s', the_trigger.name, the_event, new_value)

        match(the_trigger):
            case self.heartbeat if self.total_cycle_timer.is_running:
                self.ozone_switch.on = True
                logging.info(f'{datetime.now()} heartbeat - ozone on')
                self.ozone_on_timer.add_time()
            case self.ozone_on_timer:
                self.ozone_switch.on = False
                logging.info(f'{datetime.now()} ozone_timer - ozone off')
            case self.total_cycle_timer:
                self.ozone_on_timer.cancel()
                self.ozone_switch.on = False
                logging.info(f'{datetime.now()} total_cycle_timer - ozone off')
                self.end_of_cycle_timer.add_time()
            case self.end_of_cycle_timer:
                logging.info(f'{datetime.now()} end_of_cycle_timer - shutdown')
                exit(0)


def main(config, rule_system):

    ozone_rule = OzoneRule(
        config,
        rule_system,
        'ozone_generation_rule'
    )
    rule_system.add_rule(ozone_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
