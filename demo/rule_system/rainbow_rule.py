#!/usr/bin/env python3
import logging


from pywot.rules import (
    Rule,
    run_main,
)

from pywot.rule_triggers import HeartBeat

a_rainbow_of_colors = [
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
    '#ff0000', '#ff0008', '#ff0010', '#ff0019', '#ff0022', '#ff002a',
    '#ff0033', '#ff003b', '#ff0043', '#ff004c', '#ff0054', '#ff005d',
    '#ff0066', '#ff006e', '#ff0077', '#ff007f', '#ff0087', '#ff0090',
    '#ff0098', '#ff00a1', '#ff00aa', '#ff00b2', '#ff00bb', '#ff00c3',
    '#ff00cb', '#ff00d4', '#ff00dc', '#ff00e5', '#ff00ee', '#ff00f6',
    '#ff00ff', '#f600ff', '#ee00ff', '#e500ff', '#dc00ff', '#d400ff',
    '#cb00ff', '#c300ff', '#bb00ff', '#b200ff', '#aa00ff', '#a100ff',
    '#9800ff', '#9000ff', '#8700ff', '#7f00ff', '#7700ff', '#6e00ff',
    '#6600ff', '#5d00ff', '#5400ff', '#4c00ff', '#4300ff', '#3b00ff',
    '#3300ff', '#2a00ff', '#2200ff', '#1900ff', '#1000ff', '#0800ff',
    '#0000ff', '#0008ff', '#0011ff', '#0019ff', '#0021ff', '#002aff',
    '#0033ff', '#003bff', '#0043ff', '#004cff', '#0055ff', '#005dff',
    '#0065ff', '#006eff', '#0077ff', '#007fff', '#0087ff', '#0090ff',
    '#0099ff', '#00a1ff', '#00a9ff', '#00b2ff', '#00bbff', '#00c3ff',
    '#00cbff', '#00d4ff', '#00ddff', '#00e5ff', '#00edff', '#00f6ff',
    '#00ffff', '#00fff6', '#00ffed', '#00ffe5', '#00ffdd', '#00ffd4',
    '#00ffcb', '#00ffc3', '#00ffbb', '#00ffb2', '#00ffa9', '#00ffa1',
    '#00ff99', '#00ff90', '#00ff87', '#00ff7f', '#00ff77', '#00ff6e',
    '#00ff65', '#00ff5d', '#00ff55', '#00ff4c', '#00ff43', '#00ff3b',
]


class RainbowRule(Rule):

    def initial_state(self):
        self.participating_bulbs = (
            self.Philips_HUE_01,
            self.Philips_HUE_02,
            self.Philips_HUE_03,
            self.Philips_HUE_04,
            self.Philips_HUE_05,
            self.Philips_HUE_06,
        )

        i = 0
        for a_bulb in self.participating_bulbs:
            a_bulb.on = True
            a_bulb.color_index = i
            a_bulb.color = a_rainbow_of_colors[i]
            i += 40

    def register_triggers(self):
        self.heartbeat = HeartBeat('heartbeat', "2s")
        return (self.heartbeat, )

    def action(self, *args):
        for a_bulb in self.participating_bulbs:
            a_bulb.color_index += 40
            new_color = a_rainbow_of_colors[a_bulb.color_index % len(a_rainbow_of_colors)]
            logging.debug('%s gets new color %s', a_bulb.name, new_color)
            a_bulb.color = new_color

def main(config, rule_system):
    my_rule = RainbowRule(rule_system, 'Rainbow Rule')
    rule_system.add_rule(my_rule)


if __name__ == '__main__':
    run_main(main)
    logging.debug('done.')
