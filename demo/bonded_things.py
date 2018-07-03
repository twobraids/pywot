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

from configman import (
    Namespace,
    configuration
)
from configman.converters import (
    str_to_list,
)
from pywot import (
    logging_config,
    log_config
)

# We open a web socket to each light so we can get notified of any state change.  On noting a
# state change, we set that state in each of the other lights.  However, setting the state in
# the other lights will also induce state change messages, those need to be suppressed or
# we'll get a run away positive feedback situation.  Each time a state change is detected,
# a True value is pushed onto the 'supress_state_change' list for each one of the slaved lights.
# Before a light progates a reported state change, if there is anything in the
# 'supress_state_change' list, the list is popped by one, and the state change is not
# propagated further.
supress_state_change = []


async def monitor_and_propagate_state(config, thing_id):
    while True:
        # loop forever to re-establish the web socket if it fails for some reason
        try:
            async with websockets.connect(
                'ws://gateway.local/things/{}?jwt={}'.format(
                    thing_id,
                    config.things_gateway_auth_key
                ),
            ) as websocket:
                async for message in websocket:
                    if supress_state_change:
                        logging.debug('%s suppress action', thing_id)
                        supress_state_change.pop()
                        continue
                    logging.debug(message)
                    raw = json.loads(message)
                    if raw['messageType'] == 'propertyStatus':
                        a_property = list(raw["data"].keys())[0]
                        a_value = raw["data"][a_property]
                        logging.debug("propagate send %s %s", a_property, a_value)
                    for i in range(len(config.list_of_thing_ids) - 1):
                        # put as many True values as we have bonded things
                        supress_state_change.append(True)
                    change_property_for_all_things(config, thing_id, a_property, a_value)
        except websockets.exceptions.ConnectionClosed:
            # the connection has unexpectedly closed.
            # re-establish it by continuing the loop
            continue


def change_property_for_all_things(config, master_thing_id, a_property, a_value):
    for a_thing_id in config.list_of_thing_ids:
        if a_thing_id != master_thing_id:
            asyncio.ensure_future(change_property(config, a_thing_id, a_property, a_value))


def quote_strings(value):
    if isinstance(value, str):
        return '"{}"'.format(value)
    return value


async def change_property(config, a_thing, a_property, a_value):
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
                            str(quote_strings(a_value)).lower()
                        )
                    ) as response:
                        logging.debug('sent %s', '{{"{}": {}}}'.format(
                            a_property,
                            str(quote_strings(a_value)).lower()
                        ))
                        return await response.text()
        except aiohttp.client_exceptions.ClientConnectorError as e:
            logging.error('problem contacting http:/gateway.local: {}'.format(e))
            logging.info('retrying after 20 second pause')
            asyncio.sleep(20.0)


async def bond_things_together(config):
    logging.debug('list: %s', config.list_of_thing_ids)
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
