import aiohttp
import async_timeout
import asyncio
import logging
import websockets
import json
import string
import re

from functools import partial
from pytz import timezone

from configman.dotdict import DotDict
from configman import (
    RequiredConfig,
    Namespace,
    configuration,
    class_converter
)
from pywot import (
    logging_config,
    log_config
)


class RuleSystem(RequiredConfig):
    required_config = Namespace()
    required_config.add_option(
        'things_gateway_auth_key',
        doc='the api key to access the Things Gateway',
        short_form="G",
        default='THINGS GATEWAY AUTH KEY',
    )
    required_config.add_option(
        'seconds_for_timeout',
        doc='the number of seconds to allow for fetching data',
        default=10
    )
    required_config.add_option(
        'http_things_gateway_host',
        doc='a URL for fetching all things data',
        default="http://gateway.local",
    )
    required_config.add_option(
        "system_timezone",
        default='UTC',
        doc="the name of the default timezone running on the system ('US/Pacific, UTC, ...')",
        from_string_converter=timezone
    )
    required_config.add_option(
        "local_timezone",
        default='US/Pacific',
        doc="the name of the timezone where the Things are ('US/Pacific, UTC, ...')",
        from_string_converter=timezone
    )

    def __init__(self, config):
        self.config = config

    async def initialize(self):
        self.all_things = await self.get_all_things()
        self.set_of_participating_things = set(self.all_things)

    def find_in_all_things(self, name_of_thing):
        for a_thing in self.all_things:
            if a_thing.name == name_of_thing:
                return a_thing
        raise Exception('{} Cannot be found in all_things'.format(name_of_thing))

    def add_rule(self, a_rule):
        for a_thing in a_rule.triggering_things.values():
            a_thing.participating_rules.append(a_rule)
            self.set_of_participating_things.add(a_thing)

    async def get_all_things(self):
        async with aiohttp.ClientSession() as session:
            async with async_timeout.timeout(self.config.seconds_for_timeout):
                async with session.get(
                    '{}/things'.format(self.config.http_things_gateway_host),
                    headers={
                        'Accept': 'application/json',
                        'Authorization': 'Bearer {}'.format(self.config.things_gateway_auth_key),
                        'Content-Type': 'application/json'
                    }
                ) as response:
                    all_things_meta = json.loads(await response.text())
        # each thing needs a list of participating_rules.  The participating_rules are rules
        # that use  the things in their predicates.  Each thing that has participating_rules
        # will have an async function to respond to state changes.  This async function will
        # iterate through the list of listening rules applying the predicate and if the
        # predicate becomes True, then starting the async action.
        all_things = []
        for a_thing_meta in all_things_meta:
            a_thing = make_thing(self.config, a_thing_meta)
            all_things.append(a_thing)
        return all_things

    async def go(self):
        logging.debug('go')
        for a_trigger in self.set_of_participating_things:
            try:
                asyncio.ensure_future(
                    a_trigger.trigger_detection_loop()
                )
            except AttributeError:
                # is not required to have a trigger_detection_loop
                # this error can be ignored
                pass


def as_python_identifier(a_name):
    a_name = re.sub('[\\s\\t\\n]+', '_', a_name)
    for a_character in string.punctuation:
        a_name = a_name.replace(a_character, '_')
    if a_name[0] in '0123456789':
        a_name = "_{}".format(a_name)
    return a_name


class Thing:
    # a base class for a family of objects representing Things managed by the
    # Things Gateway.  These objects will be defined at run time using the
    # DerivedThing class within this module's 'make_thing' method
    pass


class Rule:
    def __init__(self, config, rule_system, name):
        self.config = config
        self.rule_system = rule_system
        self.name = name
        # these are the things that will trigger the rule when they
        # change state.
        self.triggering_things = {}

        # entirely for convenience, put all potential things into the rule object
        # as instance variables, this makes rules clearer to write
        for a_thing in self.rule_system.all_things:
            setattr(self, as_python_identifier(a_thing.name), a_thing)

        # go through the iterable of triggering_things and set up a key/value
        # store of them with name as the key and the thing itself as the value
        for a_triggering_thing in self.register_triggers():
            if isinstance(a_triggering_thing, str):
                # if we've gotten a string, we assume it is the name of a
                # thing in the Things Gateway.
                name = a_triggering_thing
                try:
                    self.triggering_things[name] = self.find_thing(name)
                except KeyError as e:
                    logging.info('"%s" cannot be found in the list of all_things', name)
            else:
                # it wasn't a string so we're going to assume it already is an
                # thing-like object.  No matter what type of object it is, it must
                # have a "name" attribute.
                name = a_triggering_thing.name
                self.triggering_things[name] = a_triggering_thing
                if not isinstance(a_triggering_thing, Thing):
                    # make sure we can refrence all the triggering things in the form
                    # self.thing_name.  Since objects of type Thing were setup this way
                    # earlier, don't be redundant and do it again.
                    setattr(
                        self,
                        as_python_identifier(a_triggering_thing.name),
                        a_triggering_thing
                    )

        self.initial_state()

    def initial_state(self):
        pass

    def register_triggers(self,):
        return ()

    def find_thing(self, a_thing_name):
        return self.rule_system.find_in_all_things(a_thing_name)

    def action(self, *args):
        pass


def make_thing(config, meta_definition):
    # meta_definition comes from the json representation of the thing
    meta_definiton_as_dot_dict = DotDict(meta_definition)
    # sanitize so that all keys are proper Python identifiers
    for a_key in list(meta_definiton_as_dot_dict.keys_breadth_first()):
        if ' ' in a_key or '@' in a_key:
            value = meta_definiton_as_dot_dict[a_key]
            del meta_definiton_as_dot_dict[a_key]
            replacement_key = as_python_identifier(a_key)

            meta_definiton_as_dot_dict[replacement_key] = value

    class DerivedThing(Thing):
        def __init__(self, config):
            self.config = config
            # meta_definition comes from the json representation of the thing
            self.meta_definition = meta_definiton_as_dot_dict
            self.id = self.meta_definition.href.split('/')[-1]
            self.name = self.meta_definition.name
            self.participating_rules = []

        @staticmethod
        def quote_strings(a_value):
            if isinstance(a_value, str):
                return '"{}"'.format(a_value)
            return a_value

        async def async_change_property(self, a_property_name, a_value):
            while True:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with async_timeout.timeout(self.config.seconds_for_timeout):
                            async with session.put(
                                "{}/things/{}/properties/{}/".format(
                                    self.config.http_things_gateway_host,
                                    self.id,
                                    a_property_name
                                ),
                                headers={
                                    'Accept': 'application/json',
                                    'Authorization': 'Bearer {}'.format(
                                        self.config.things_gateway_auth_key
                                    ),
                                    'Content-Type': 'application/json'
                                },
                                data='{{"{}": {}}}'.format(
                                    a_property_name,
                                    str(self.quote_strings(a_value)).lower()
                                )
                            ) as response:
                                return await response.text()
                except aiohttp.client_exceptions.ClientConnectorError as e:
                    logging.error(
                        'change_property: problem contacting http://gateway.local: %s', e
                    )
                    logging.info('change_property: retrying after 20 second pause')
                    await asyncio.sleep(20.0)

        async def trigger_detection_loop(self):
            while True:
                try:
                    async with websockets.connect(
                        '{}?jwt={}'.format(
                            self.web_socket_link,
                            self.config.things_gateway_auth_key
                        ),
                    ) as websocket:
                        logging.info('web socket established to %s', self.web_socket_link)
                        async for message in websocket:
                            raw = json.loads(message)
                            if raw['messageType'] == 'propertyStatus':
                                message = raw['data']
                                self.process_property_status_message(message)
                except Exception as e:
                    # if the connection fails for any reason, reconnect
                    logging.error('web socket failure (%s): %s', self.web_socket_link, e)
                    logging.info('waiting 30S to retry web socket to: %s', self.web_socket_link)
                    await asyncio.sleep(30)

        def update_hidden_property(self, a_property_name, new_value):
            hidden_property_name = self.hidden_property_names[a_property_name]
            logging.debug('%s setting %s to %s', self.name, hidden_property_name, new_value)
            setattr(self, hidden_property_name, new_value)

        def process_property_status_message(self, message):
            for a_property_name, new_value in message.items():
                self.update_hidden_property(a_property_name, new_value)
                self._apply_rules(a_property_name, new_value)

        def _apply_rules(self, a_property_name, a_value):
            for a_rule in self.participating_rules:
                a_rule.action(self, a_property_name, a_value)

    def get_property(hidden_instance_name, self):
        return getattr(self, hidden_instance_name)

    def change_property(a_property_name, hidden_instance_name, self, a_value):
        if a_value != getattr(self, hidden_instance_name):
            asyncio.ensure_future(
                self.async_change_property(a_property_name, a_value)
            )
            logging.info('%s setting %s to %s', self.name, a_property_name, a_value)
            setattr(self, hidden_instance_name, a_value)
            self._apply_rules(a_property_name, a_value)

    DerivedThing.hidden_property_names = {}
    for a_property_name in meta_definition['properties'].keys():
        a_python_property_name = as_python_identifier(a_property_name)
        hidden_instance_name = '__{}'.format(a_python_property_name)
        DerivedThing.hidden_property_names[a_property_name] = hidden_instance_name
        DerivedThing.hidden_property_names[a_python_property_name] = hidden_instance_name
        setattr(
            DerivedThing,
            a_python_property_name,
            property(
                partial(get_property, hidden_instance_name),
                partial(change_property, a_python_property_name, hidden_instance_name)
            )
        )

    the_thing = DerivedThing(config)

    # find the websocket URI
    for a_link_dict in the_thing.meta_definition.links:
        if a_link_dict['rel'] == "alternate" and a_link_dict['href'].startswith('ws'):
            the_thing.web_socket_link = a_link_dict['href']

    for a_property_name in meta_definition['properties'].keys():
        a_python_property_name = as_python_identifier(a_property_name)
        hidden_instance_name = '__{}'.format(a_python_property_name)
        setattr(the_thing, hidden_instance_name, None)
    return the_thing


def run_main(main_function, configuration_requirements=Namespace()):
    required_config = Namespace()
    required_config.add_option(
        'rule_system_class',
        doc='the fully qualified name of the RuleSystem class',
        default=RuleSystem,
        from_string_converter=class_converter,
    )
    required_config.update(logging_config)
    required_config.update(configuration_requirements)
    config = configuration(required_config)

    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format
    )
    log_config(config)

    rule_system = config.rule_system_class(config)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(rule_system.initialize())
    main_function(config, rule_system)
    loop.run_until_complete(rule_system.go())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
