#!/usr/bin/env python3

"""This Web Thing implements a solar panel monitoring Thing for the Things Gateway from Mozilla.

--help will give a complete listing of the options.
--enphase_address=<local network enphase address> to set the IP address of the Enphase Web
    server on the local network.
--admin.dump_conf=my_config.ini  will create an ini file that then can be edited to
    set the parameters.
--admin.conf=my_config.ini will thereafter load configuration from the file.
"""

import aiohttp
import async_timeout
import asyncio
import logging
import json
import websockets

from pywot import (
    WoTThing,
    logging_config,
    log_config
)
from configmanners import (
    configuration,
    Namespace,
    class_converter,
)

ON = True
OFF = False


def scene_on_off(thing_instance, on_off):
    if on_off is ON:
        asyncio.ensure_future(thing_instance.turn_on_participants())
    else:
        asyncio.ensure_future(thing_instance.restore_participants())


def learn_on_off(thing_instance, on_off):
    if on_off is ON:
        asyncio.ensure_future(thing_instance.learn_changes())
    else:
        asyncio.ensure_future(thing_instance.stop_learning())


class SceneThing(WoTThing):
    required_config = Namespace()
    required_config.add_option(
        'all_things_url',
        doc='a URL for fetching all things data',
        default="http://gateway.local/things",
    )
    required_config.add_option(
        'thing_state_url_template',
        doc='a URL for fetching the current state of a thing',
        default="http://gateway.local/things/{}/properties/{}",
    )
    required_config.add_option(
        'seconds_for_timeout',
        doc='the number of seconds to allow for fetching enphase data',
        default=10
    )

    def __init__(self, config):
        super(SceneThing, self).__init__(
            config,
            "Scene Thing",
            "thing",
            "A controller for scenes"
        )
        self.state_file_name = '{}.json'.format(self.name)
        try:
            with open(self.state_file_name) as state_file:
                self.participants = json.load(state_file)
        except FileNotFoundError:
            logging.info('no scene state file found for %s', self.state_file_name)
            self.participants = {}
        except json.decoder.JSONDecodeError:
            logging.info('bad file format for %s', self.state_file_name)
            self.participants = {}

        self.listeners = []
        self.preserved_state = {}

    on_off = WoTThing.wot_property(
        name='on',
        initial_value=False,
        description='on/off status',
        value_forwarder=scene_on_off,

    )
    learn = WoTThing.wot_property(
        name='learn',
        initial_value=False,
        description='learn mode',
        value_forwarder=learn_on_off,
    )

    async def get_all_things(self):
        async with aiohttp.ClientSession() as session:
            async with async_timeout.timeout(self.config.seconds_for_timeout):
                async with session.get(
                    self.config.all_things_url,
                    headers={
                        'Accept': 'application/json',
                        'Authorization': 'Bearer {}'.format(self.config.things_gateway_auth_key),
                        'Content-Type': 'application/json'
                    }
                ) as response:
                    all_things = json.loads(await response.text())
                    print(json.dumps(all_things))
                    return all_things

    @staticmethod
    def quote_strings(a_value):
        if isinstance(a_value, str):
            return '"{}"'.format(a_value)
        return a_value

    async def change_property(self, a_thing_id, a_property, a_value):
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with async_timeout.timeout(self.config.seconds_for_timeout):
                        async with session.put(
                            "http://gateway.local/things/{}/properties/{}/".format(
                                a_thing_id,
                                a_property
                            ),
                            headers={
                                'Accept': 'application/json',
                                'Authorization': 'Bearer {}'.format(
                                    self.config.things_gateway_auth_key
                                ),
                                'Content-Type': 'application/json'
                            },
                            data='{{"{}": {}}}'.format(
                                a_property,
                                str(self.quote_strings(a_value)).lower()
                            )
                        ) as response:
                            logging.debug(
                                'change_property: sent %s to %s',
                                '{{"{}": {}}}'.format(
                                    a_property,
                                    str(self.quote_strings(a_value)).lower()
                                ),
                                a_thing_id
                            )
                            return await response.text()
            except aiohttp.client_exceptions.ClientConnectorError as e:
                logging.error(
                    'change_property: problem contacting http:/gateway.local: {}'.format(e)
                )
                logging.info('change_property: retrying after 20 second pause')
                await asyncio.sleep(20.0)

    async def change_properties_from_a_change_set(self, a_thing_id, a_change_set):
        # it seems that some devices cannot have properties changed if they are
        # on in their 'on' state.  If the change_set contains a property to turn
        # the thing on, do that first.
        if 'on' in a_change_set and a_change_set['on'] is True:
            await self.change_property(a_thing_id, 'on', True)
        await asyncio.gather(*(
            self.change_property(a_thing_id, a_property, a_value)
            for a_property, a_value in a_change_set.items()
            if a_property != 'on'
        ))
        # if the change_set has an 'on' property to turn something off, ensure that
        # turning the thing off is the last thing done.
        if 'on' in a_change_set and a_change_set['on'] is False:
            await self.change_property(a_thing_id, 'on', False)

    async def monitor_state(self, a_thing_id):
        async with websockets.connect(
            'ws://gateway.local/things/{}?jwt={}'.format(
                a_thing_id,
                self.config.things_gateway_auth_key
            ),
        ) as websocket:
            async for message in websocket:
                raw = json.loads(message)
                if raw['messageType'] == 'propertyStatus':
                    if a_thing_id in self.participants:
                        self.participants[a_thing_id].update(raw["data"])
                    else:
                        self.participants[a_thing_id] = raw["data"]

    async def learn_changes(self):
        # connect to Things Gateway and create listener for every object and property
        all_things = await self.get_all_things()
        for a_thing in all_things:
            if a_thing['name'] == self.name:
                logging.debug('skipping thing %s', a_thing['name'])
                continue
            a_thing_id = a_thing['href'].replace('/things/', '')
            self.listeners.append(
                asyncio.ensure_future(self.monitor_state(a_thing_id))
            )

    async def stop_learning(self):
        # close all listeners
        asyncio.gather(*self.listeners, return_exceptions=True).cancel()
        logging.info('stop_learing:  this is what I learned:')
        for a_thing_id, a_change_set in self.participants.items():
            logging.info('    {}: {}'.format(a_thing_id, a_change_set))
        with open(self.state_file_name, 'w') as state_file:
            json.dump(self.participants, state_file)

    async def capture_current_state(self, a_thing_id, a_change_set):
        self.preserved_state[a_thing_id] = {}
        for a_property in a_change_set.keys():
            # as of 0.4, the 'properties' resource has not been implemented in the Things API
            # this means that rather than fetching all the properties for a thing in one call
            # we've got to do it one property at a time.
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(self.config.seconds_for_timeout):
                    logging.debug(self.config.thing_state_url_template.format(a_thing_id, a_property))
                    async with session.get(
                        self.config.thing_state_url_template.format(a_thing_id, a_property),
                        headers={
                            'Accept': 'application/json',
                            'Authorization': 'Bearer {}'.format(self.config.things_gateway_auth_key),
                            'Content-Type': 'application/json'
                        }
                    ) as response:
                        state_snapshot = json.loads(await response.text())
                        self.preserved_state[a_thing_id].update(state_snapshot)

    async def turn_on_participants(self):
        if self.learn == ON:
            self.learn = OFF
        # go through participants, capturing their current state
        self.preserved_state = {}
        await asyncio.gather(*(
            self.capture_current_state(a_thing, a_change_set)
            for a_thing, a_change_set in self.participants.items()
        ))
        # go through participtants setting their state
        logging.debug('start turn_on_participants')
        await asyncio.gather(*(
            self.change_properties_from_a_change_set(a_thing, change_set)
            for a_thing, change_set in self.participants.items()
        ))

    async def restore_participants(self):
        # go through participants and turn off
        if self.learn == ON:
            self.learn = OFF
        await asyncio.gather(*(
            self.change_properties_from_a_change_set(a_thing, change_set)
            for a_thing, change_set in self.preserved_state.items()
        ))


if __name__ == '__main__':
    required_config = Namespace()
    required_config.server = Namespace()
    required_config.server.add_option(
        name='wot_server_class',
        default="pywot.WoTServer",
        doc="the fully qualified name of the WoT Server class",
        from_string_converter=class_converter
    )
    required_config.add_option(
        name="scene_thing_class",
        default=SceneThing,
        doc="the fully qualified name of the class that implents scene control",
        from_string_converter=class_converter
    )
    required_config.add_option(
        'things_gateway_auth_key',
        doc='the api key to access the Things Gateway',
        short_form="G",
        default='THINGS GATEWAY AUTH KEY',
    )
    required_config.update(logging_config)
    config = configuration(required_config)

    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format
    )
    log_config(config)

    scene_thing = config.scene_thing_class(config)

    server = config.server.wot_server_class(
        config,
        [scene_thing],
        port=config.server.service_port
    )
    server.run()
    logging.debug('done.')
