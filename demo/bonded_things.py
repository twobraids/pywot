#!/usr/bin/env python3

# Demonstrate the Things API by making a set of Philips HUE lights
# bonded to each other.  Any state change (on/off, color) to one
# is immediately echoed by all the others

import json
import asyncio
import aiohttp
import async_timeout
import logging
import websockets

from configmanners import (
    Namespace,
    configuration
)
from configmanners.converters import (
    str_to_list,
)
from pywot import (
    logging_config,
    log_config
)

# We open a web socket to each light so we can get notified of any state change.  On noting a
# state change, we set that state in each of the other lights.  However, setting the state in
# the other lights will also induce state change messages, those need to be suppressed or
# we'll get a run away positive feedback situation.  A solution is to use a counter.
#
# Each time a state change is detected, the detecting thread raises the counter to
# the number of Web Things in the bonded group minus one.  Thereafter, if another thread receives
# a state change message, it does not act on the message and decrements the counter.  Only when
# the counter is at zero will a thread act on a state change.
suppress_state_change = 0


async def monitor_and_propagate_state(config, thing_id):
    global suppress_state_change
    suppress_state_change_max = len(config.list_of_thing_ids) - 1
    while True:
        # loop forever to re-establish the web socket if it fails for some reason
        try:
            async with websockets.connect(
                'ws://gateway.local/things/{}?jwt={}'.format(
                    thing_id,
                    config.things_gateway_auth_key
                ),
            ) as websocket:
                async for a_message_txt in websocket:
                    a_message = json.loads(a_message_txt)
                    if a_message['messageType'] == 'propertyStatus':
                        if suppress_state_change:
                            logging.debug('%s suppress action', thing_id)
                            suppress_state_change -= 1
                            continue
                        for a_property in a_message["data"].keys():
                            a_value = a_message["data"][a_property]
                            logging.debug("propagate send %s %s", a_property, a_value)
                            suppress_state_change = suppress_state_change_max
                            change_property_for_all_things(config, thing_id, a_property, a_value)
        except websockets.exceptions.ConnectionClosed:
            # the connection has unexpectedly closed.
            # re-establish it by continuing the loop
            continue


def change_property_for_all_things(config, master_thing_id, a_property, a_value):
    asyncio.ensure_future(
        asyncio.gather(*(
            change_property(config, a_thing_id, a_property, a_value)
            for a_thing_id in config.list_of_thing_ids
            if a_thing_id != master_thing_id
        ))
    )


def format_for_json_output(value):
    if isinstance(value, str):
        return '"{}"'.format(value).lower()
    return str(value).lower()


async def change_property(config, a_thing, a_property, a_value):
    a_value_formatted = format_for_json_output(a_value)
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(config.seconds_for_timeout):
                    async with session.put(
                        "http://gateway.local/things/{}/properties/{}".format(
                            a_thing,
                            a_property
                        ),
                        headers={
                            'Accept': 'application/json',
                            'Authorization': 'Bearer {}'.format(config.things_gateway_auth_key),
                            'Content-Type': 'application/json'
                        },
                        data='{{"{}": {}}}'.format(
                            a_property,
                            a_value_formatted
                        )
                    ) as response:
                        logging.debug('sent %s', '{{"{}": {}}}'.format(
                            a_property,
                            a_value_formatted
                        ))
                        return await response.text()
        except aiohttp.client_exceptions.ClientConnectorError as e:
            logging.error('problem contacting http:/gateway.local: {}'.format(e))
            logging.info('retrying after 20 second pause')
            await asyncio.sleep(20.0)


async def bond_things_together(config):
    for a_thing_id in config.list_of_thing_ids:
        asyncio.ensure_future(
            monitor_and_propagate_state(config, a_thing_id)
        )


required_config = Namespace()
required_config.add_option(
    'seconds_for_timeout',
    doc='the number of seconds to allow for fetching',
    default=10
)
required_config.add_option(
    'things_gateway_auth_key',
    doc='the api key to access the Things Gateway',
    short_form="G",
    default='THINGS GATEWAY AUTH KEY',
)
required_config.add_option(
    'list_of_thing_ids',
    doc='a list of thing ids to bond together',
    default="A LIST OF THING IDS TO BOND TOGETHER",
    from_string_converter=str_to_list
)
required_config.update(logging_config)

if __name__ == '__main__':

    config = configuration(required_config)
    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format
    )
    log_config(config)

    asyncio.ensure_future(bond_things_together(config))
    asyncio.get_event_loop().run_forever()
