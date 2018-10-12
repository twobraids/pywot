#!/usr/bin/env python3
import logging

from pywot.rules import (
    Rule,
    run_main,
)

from collections import deque
from pywot.rule_triggers import HeartBeat

color_transition_values = [
    '#00ff00', '#04ff00', '#08ff00', '#0cff00', '#10ff00', '#15ff00',
    '#19ff00', '#1dff00', '#21ff00', '#26ff00', '#2aff00', '#2eff00',
    '#32ff00', '#37ff00', '#3bff00', '#3fff00', '#43ff00', '#48ff00',
    '#4cff00', '#50ff00', '#54ff00', '#59ff00', '#5dff00', '#61ff00',
    '#65ff00', '#6aff00', '#6eff00', '#72ff00', '#76ff00', '#7bff00',
    '#7fff00', '#83ff00', '#88ff00', '#8cff00', '#90ff00', '#94ff00',
    '#99ff00', '#9dff00', '#a1ff00', '#a5ff00', '#aaff00', '#aeff00',
    '#b2ff00', '#b6ff00', '#bbff00', '#bfff00', '#c3ff00', '#c7ff00',
    '#ccff00', '#d0ff00', '#d4ff00', '#d8ff00', '#ddff00', '#e1ff00',
    '#e5ff00', '#e9ff00', '#eeff00', '#f2ff00', '#f6ff00', '#faff00',
    '#ffff00', '#fffa00', '#fff600', '#fff200', '#ffee00', '#ffe900',
    '#ffe500', '#ffe100', '#ffdd00', '#ffd800', '#ffd400', '#ffd000',
    '#ffcc00', '#ffc700', '#ffc300', '#ffbf00', '#ffbb00', '#ffb600',
    '#ffb200', '#ffae00', '#ffaa00', '#ffa500', '#ffa100', '#ff9d00',
    '#ff9900', '#ff9400', '#ff9000', '#ff8c00', '#ff8800', '#ff8300',
    '#ff7f00', '#ff7b00', '#ff7700', '#ff7200', '#ff6e00', '#ff6a00',
    '#ff6600', '#ff6100', '#ff5d00', '#ff5900', '#ff5400', '#ff5000',
    '#ff4c00', '#ff4800', '#ff4300', '#ff3f00', '#ff3b00', '#ff3700',
    '#ff3200', '#ff2e00', '#ff2a00', '#ff2600', '#ff2100', '#ff1d00',
    '#ff1900', '#ff1500', '#ff1000', '#ff0c00', '#ff0800', '#ff0400',
    '#ff0000'
]
number_of_steps = len(color_transition_values)

class DeadlineRule(Rule):

    def __init__(self, rule_system, name, deadline_datetime):
        self.deadline = deadline_datetime
        self.fade_task = None
        super(DeadlineRule, self).__init__(rule_system, name)

    def initial_state(self):
        self.Philips_HUE_01.on = True
        self.Philips_HUE_01.color = color_transition_values[0]

    def register_triggers(self):

        return (self.Philips_HUE_01, )

    def action(self, the_changed_thing, the_changed_property, the_new_value):
        if the_changed_property == "on" and the_new_value is True:
            self.fade_task = asyncio.ensure_future()

    async def _change_color_by_steps(self, ):
        for i in range(number_of_steps):
            new_level = (i + 1) * 5
            self.Bedside_Ikea_Light.on = True
            self.Bedside_Ikea_Light.level = new_level
            await asyncio.sleep(60)



def main(config, rule_system):
    my_rule = RainbowRule(rule_system, 'Rainbow Rule')
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.info('done.')
