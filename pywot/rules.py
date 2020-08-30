import aiohttp
import async_timeout
import asyncio
import logging
import websockets
import json
import string
import re

from functools import partial
from time import sleep
from contextlib import contextmanager
from pytz import timezone

from configman.dotdict import DotDict
from configman import RequiredConfig, Namespace, configuration, class_converter
from pywot import logging_config, log_config
from pywot.thing_dataclass import create_dataclass


DoNotCare = None


class RuleSystem(RequiredConfig):
    required_config = Namespace()
    required_config.add_option(
        "things_gateway_auth_key",
        doc="the api key to access the Things Gateway",
        short_form="G",
        default="THINGS GATEWAY AUTH KEY",
    )
    required_config.add_option(
        "seconds_for_timeout", doc="the number of seconds to allow for fetching data", default=10
    )
    required_config.add_option(
        "http_things_gateway_host",
        doc="a URL for fetching all things data",
        default="http://gateway.local",
    )
    required_config.add_option(
        "system_timezone",
        default="UTC",
        doc="the name of the default timezone running on the system ('US/Pacific, UTC, ...')",
        from_string_converter=timezone,
    )
    required_config.add_option(
        "local_timezone",
        default="US/Pacific",
        doc="the name of the timezone where the Things are ('US/Pacific, UTC, ...')",
        from_string_converter=timezone,
    )

    def __init__(self, config):
        self.config = config

    async def initialize(self):
        self.all_things = await self.get_list_of_all_known_things()
        self.set_of_triggers_that_use_this_rule_system = set(self.all_things)
        logging.info("initialization complete")

    def find_in_all_things(self, name_of_thing):
        for a_thing in self.all_things:
            if a_thing.name == name_of_thing:
                return a_thing
        raise Exception("{} Cannot be found in all_things".format(name_of_thing))

    def add_rule(self, a_rule):
        logging.info("%s being added", a_rule.__class__.__name__)
        for a_thing in a_rule.things_that_trigger_this_rule.values():
            a_thing.rules_that_use_this_thing.append(a_rule)
            self.set_of_triggers_that_use_this_rule_system.add(a_thing)

    async def get_list_of_all_known_things(self):
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with async_timeout.timeout(self.config.seconds_for_timeout):
                        async with session.get(
                            f"{self.config.http_things_gateway_host}/things",
                            headers={
                                "Accept": "application/json",
                                "Authorization": f"Bearer {self.config.things_gateway_auth_key}",
                            },
                        ) as response:
                            definitions_of_all_things_as_list = json.loads(await response.text())
                # each thing needs a list of participating_rules.  The participating_rules are rules
                # that use  the things in their predicates.  Each thing that has participating_rules
                # will have an async function to respond to state changes.  This async function will
                # iterate through the list of listening rules applying the predicate and if the
                # predicate becomes True, then starting the async action.
                list_of_all_things = []
                for a_thing_definition_as_dict in definitions_of_all_things_as_list:
                    a_thing = make_thing(self.config, a_thing_definition_as_dict)
                    list_of_all_things.append(a_thing)
                return list_of_all_things
            except Exception as e:
                logging.error("connection  refused %s\nretrying in 30 seconds", e)
                sleep(30.0)

    async def go(self):
        logging.debug("go")
        for a_trigger in self.set_of_triggers_that_use_this_rule_system:
            logging.info("starting trigger_dectection_loop for %s", a_trigger.name)
            try:
                asyncio.ensure_future(a_trigger.trigger_detection_loop())
            except AttributeError:
                # is not required to have a trigger_detection_loop
                # this error can be ignored
                pass


def as_python_identifier(a_name):
    a_name = re.sub("[\\s\\t\\n]+", "_", a_name)
    for a_character in string.punctuation:
        a_name = a_name.replace(a_character, "_")
    if a_name[0] in "0123456789":
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
        self.things_that_trigger_this_rule = {}

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
                    self.things_that_trigger_this_rule[name] = self.find_thing(name)
                except KeyError as e:
                    logging.info('"%s" cannot be found in the list of all_things', name)
            else:
                # it wasn't a string so we're going to assume it already is an
                # thing-like object.  No matter what type of object it is, it must
                # have a "name" attribute.
                name = a_triggering_thing.name
                self.things_that_trigger_this_rule[name] = a_triggering_thing
                if not isinstance(a_triggering_thing, Thing):
                    # make sure we can refrence all the triggering things in the form
                    # self.thing_name.  Since objects of type Thing were setup this way
                    # earlier, don't be redundant and do it again.
                    setattr(self, as_python_identifier(a_triggering_thing.name), a_triggering_thing)

        self.initial_state()

    def initial_state(self):
        pass

    def register_triggers(self,):
        return ()

    def find_thing(self, a_thing_name):
        return self.rule_system.find_in_all_things(a_thing_name)

    def action(self, *args):
        pass


def make_thing(config, thing_definition_as_dict):
    # thing_definition_as_dict comes from the json representation of the thing
    # Keys in Python dicts, unlike the Javascript equivalent, can only be accessed
    # by using the [] syntax. By recasting the dict as a DotDict, we get the ability
    # to access keys using "." syntax.
    thing_definiton_as_dot_dict = DotDict(thing_definition_as_dict)
    # sanitize so that all keys are proper Python identifiers
    for a_key in list(thing_definiton_as_dot_dict.keys_breadth_first()):
        if " " in a_key or "@" in a_key or "-" in a_key:
            value = thing_definiton_as_dot_dict[a_key]
            del thing_definiton_as_dot_dict[a_key]
            replacement_key = as_python_identifier(a_key)

            thing_definiton_as_dot_dict[replacement_key] = value

    class ThingTalker(Thing):
        """This class embodies the RuleSystem's implementation of a Thing from the Things Gateway.
        It makes the Things' Things Gateway properties accessible via dot notation (thing.property)"""
        def __init__(self, config):
            self.config = config
            # thing_definiton_as_dot_dict comes from the json representation of the thing from the
            # Things Gateway
            self.thing_definition_as_dot_dict = thing_definiton_as_dot_dict
            self.id = self.thing_definition_as_dot_dict.href.split("/")[-1]
            self.name = self.thing_definition_as_dot_dict.title
            self.rules_that_use_this_thing = []
            self.command_queue = asyncio.Queue()
            self.dataclass = create_dataclass(
                f"{self.name}DataClass", self.thing_definition_as_dot_dict
            )
            self.connection_acknowledged = False

        @staticmethod
        def quote_strings(a_value):
            if isinstance(a_value, str):
                return f'"{a_value}"'
            return a_value

        def state(self):
            "create a dataclass as a snapshot of current state"
            a_thing_state_as_dict = self.dataclass.a_thing_state_as_dict(self)
            return self.dataclass(**a_thing_state_as_dict)

        async def async_change_property(self, a_property_name, a_value):
            message_as_dict = {"messageType": "setProperty", "data": {a_property_name: a_value}}
            logging.debug("queue put %s: %s", self.name, message_as_dict)
            await self.command_queue.put(message_as_dict)

        async def receive_websocket_messages(self, websocket):
            async for message_as_string in websocket:
                message_as_dict = json.loads(message_as_string)
                message_data_as_dict = message_as_dict["data"]
                if message_as_dict["messageType"] == "propertyStatus":
                    logging.info("property status %s.%s", self.name, message_as_dict)
                    self.process_property_status_message(message_data_as_dict)
                elif message_as_dict["messageType"] == "event":
                    self.process_event_message(message_data_as_dict)
                elif message_as_dict["messageType"] == "connected":
                    self.connection_acknowledged = message_as_dict["data"]

        async def send_queued_messages(self, websocket):
            while True:
                # ugh, polling is bad, rethink this
                if not self.connection_acknowledged:
                    logging.info("%s (%s) waiting for connection", self.name, self.id)
                    await asyncio.sleep(2)
                    continue
                command = await self.command_queue.get()
                command_as_string = json.dumps(command)
                logging.info("%s (%s) sending: %s", self.name, self.id, command_as_string)
                await websocket.send(command_as_string)
                await asyncio.sleep(0.25)

        async def trigger_detection_loop(self):
            while True:
                try:
                    logging.info("creating Web Socket %s", self.web_socket_uri)
                    async with websockets.connect(
                        "{}?jwt={}".format(
                            self.web_socket_uri, self.config.things_gateway_auth_key
                        ),
                    ) as websocket:
                        logging.info("Web Socket established to %s", self.web_socket_uri)
                        await asyncio.gather(
                            self.receive_websocket_messages(websocket),
                            self.send_queued_messages(websocket),
                        )

                except Exception as e:
                    # if the connection fails for any reason, reconnect
                    logging.error("web socket failure (%s): %s", self.web_socket_uri, e)
                    logging.info("waiting 30S to retry web socket to: %s", self.web_socket_uri)
                    await asyncio.sleep(30)
                    # raise

        def subscribe_to_event(self, event_name):
            asyncio.ensure_future(self.async_subscribe_to_event(event_name))

        async def async_subscribe_to_event(self, event_name):
            try:
                event_subscription = {
                    "messageType": "addEventSubscription",
                    "data": {event_name: {}},
                }
                string = json.dumps(event_subscription)
                logging.info("queue put %s: %s", self.name, event_subscription)
                await self.command_queue.put(event_subscription)

            except Exception as e:
                logging.error(e)

        def update_hidden_property(self, a_property_name, new_value):
            hidden_property_name = self.hidden_property_names[a_property_name]
            logging.debug("%s setting %s to %s", self.name, hidden_property_name, new_value)
            setattr(self, hidden_property_name, new_value)

        def process_property_status_message(self, message):
            logging.debug("%s property_change: %s", self.name, message)
            for a_property_name, new_value in message.items():
                self.update_hidden_property(a_property_name, new_value)
                self._apply_rules(a_property_name, new_value)

        def process_event_message(self, message):
            logging.debug("process_event_message: %s", message)
            for event_name in message.keys():
                self._apply_rules(event_name)

        def _apply_rules(self, a_property_name, a_value=None):
            for a_rule in self.rules_that_use_this_thing:
                a_rule.action(self, a_property_name, a_value)

        def set(self, a_dataclass):
            message = {"messageType": "setProperty", "data": a_dataclass.as_dict()}
            logging.info("queue put %s: %s", self.name, message)
            asyncio.ensure_future(self.command_queue.put(message))

        @contextmanager
        def batch_communication(self):
            thing_proxy = DotDict()
            try:
                yield thing_proxy
            finally:
                message = {"messageType": "setProperty", "data": {}}
                for key in thing_proxy.keys_breadth_first():
                    message["data"][key] = thing_proxy[key]
                logging.info("queue put %s: %s", self.name, message)
                asyncio.ensure_future(self.command_queue.put(message))

    def get_property(hidden_instance_name, self):
        return getattr(self, hidden_instance_name)

    def change_property(a_property_name, hidden_instance_name, self, a_value):
        # if a_value != getattr(self, hidden_instance_name):
        asyncio.ensure_future(self.async_change_property(a_property_name, a_value))
        logging.debug("%s setting %s to %s", self.name, a_property_name, a_value)
        setattr(self, hidden_instance_name, a_value)

    ThingTalker.hidden_property_names = {}
    for a_property_name in thing_definition_as_dict["properties"].keys():
        a_python_property_name = as_python_identifier(a_property_name)
        hidden_instance_name = "__{}".format(a_python_property_name)
        ThingTalker.hidden_property_names[a_property_name] = hidden_instance_name
        ThingTalker.hidden_property_names[a_python_property_name] = hidden_instance_name
        setattr(
            ThingTalker,
            a_python_property_name,
            property(
                partial(get_property, hidden_instance_name),
                partial(change_property, a_python_property_name, hidden_instance_name),
            ),
        )

    the_thing = ThingTalker(config)

    # find the websocket URI
    for a_link_dict in the_thing.thing_definition_as_dot_dict.links:
        if a_link_dict["rel"] == "alternate" and a_link_dict["href"].startswith("ws"):
            the_thing.web_socket_uri = a_link_dict["href"]

    for a_property_name in thing_definition_as_dict["properties"].keys():
        a_python_property_name = as_python_identifier(a_property_name)
        hidden_instance_name = "__{}".format(a_python_property_name)
        setattr(the_thing, hidden_instance_name, None)
    return the_thing


def run_main(main_function, configuration_requirements=Namespace()):
    required_config = Namespace()
    required_config.add_option(
        "rule_system_class",
        doc="the fully qualified name of the RuleSystem class",
        default=RuleSystem,
        from_string_converter=class_converter,
    )
    required_config.update(logging_config)
    required_config.update(configuration_requirements)
    config = configuration(required_config)

    logging.basicConfig(level=config.logging_level, format=config.logging_format)
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
