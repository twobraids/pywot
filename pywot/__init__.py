from webthing import (
    Thing,
    MultipleThings,
    Property,
    SingleThing,
    Value,
    WebThingServer,
)
from asyncio import (
    sleep,
    gather,
    get_event_loop,
    CancelledError
)
from configman import (
    Namespace,
    RequiredConfig
)
from configman.converters import to_str
from functools import partial
from itertools import filterfalse
from collections import Mapping
import logging


def pytype_as_wottype(example_value):
    """given a value of a basic type, return the string
    representing the type in the Things Gateway"""
    return {
        int: 'number',
        str: 'string',
        float: 'number',
        bool: 'boolean',
        type(None): 'string',
    }[type(example_value)]


class WoTProperty:
    """This class is a descriptor containing all of the required resources of a webthing.Property"""
    def __init__(
        self,
        *,
        name,
        initial_value,
        description,
        value_source_fn=None,
        value_forwarder=None,
        **kwargs
    ):
        # WoT Properties must be instantiated when the Thing is instantiated.  Since this code runs
        # at class load time, we must just save the parameters for a future instantiation.  We do
        # this with a partial of the `create_wot_property` and save it as an attribute to be used
        # at a later time
        self.wot_property_creation_function = partial(
            self.create_wot_property,
            name=name,
            initial_value=initial_value,
            description=description,
            value_source_fn=value_source_fn,
            value_forwarder=value_forwarder,
            **kwargs
        )
        self.name = name
        if value_source_fn is not None:
            # since this Wot Property has its own function for a source of values, it will need an
            # async loop to poll for the values.  We define it here as a closure over that
            # the `value_source_fn`.  It will be executed only after instantiation by the server
            # and the first parameter is an instance of Thing, we're effectively making a new
            # instance method for the WoTThing class.  Ideally, this should be a member of the
            # of the WoTThing class and may well move there in the future.
            async def a_property_fetching_coroutine(thing_instance):
                while True:
                    try:
                        await value_source_fn(thing_instance)
                    except CancelledError:
                        logging.debug('cancel detected')
                        break
                    except Exception as e:
                        logging.error('loading data fails: %s: %s', type(e), e)
                        # we'll be optimistic and prefer to retry if something goes wrong.
                        # while graceful falure is to be commended, there is also great value
                        # in spontaneous recovery.
                    await sleep(thing_instance.config.seconds_between_polling)

            # since there may be more that one `a_property_fetching_task`, it gets tagged
            # so that we can get more helpful debugging and logging information
            a_property_fetching_coroutine.property_name = name
            self.property_fetching_coroutine = a_property_fetching_coroutine

    def __get__(self, thing_instance, objtype=None):
        # to serve as a Python descriptor, there must be a __get__ method to return the
        # target value from the underlying WoT Thing instance.
        if thing_instance is None:
            return self
        return thing_instance.properties[self.name].value.get()

    def __set__(self, thing_instance, new_value):
        # to serve as a Python descriptor, we provide a __set__ method to set a new value
        # for the Property in the underlying WoT Thing instance.
        thing_instance.properties[self.name].value.notify_of_external_update(new_value)

    def create_wot_property(
        self,
        thing_instance,
        *,
        name,
        initial_value,
        description,
        value_source_fn=None,
        value_forwarder=None,
        **kwargs
    ):
        """this method is used to add a new Thing Property to an intializing instance of a WoTThing.
        It is invoked as a partial functon"""
        if value_forwarder is None:
            value = Value(initial_value)
        else:
            logging.debug('CREATING property {} with initial value {}'.format(name, initial_value))
            value = Value(initial_value, value_forwarder=partial(value_forwarder, thing_instance))
            logging.debug('new value {} is {}'.format(name, value.last_value))
        property_metadata = {
            "type": pytype_as_wottype(initial_value),
            "description": description,
        }
        if kwargs:
            property_metadata.update(kwargs)
        thing_instance.add_property(
            Property(
                thing_instance,
                name,
                value,
                property_metadata
            )
        )


class WoTThing(Thing, RequiredConfig):
    """This class mixes in the Configman configuration API into the Things Gateway Thing class
    It also provides the mechanism that allows Thing properties to be specified during a derived
    classes loading time, but not instantiated until a derived class instance initialization. This
    allows Thing properties to work like traditional Python `properties`.  That, in turn,
    simplifies the task of the author of the derived class and makes for more readable code."""
    required_config = Namespace()
    required_config.add_option(
        'seconds_between_polling',
        doc='the number of seconds between each time polling',
        default=300
    )

    def __init__(self, config, name, type_, description):
        self.config = config
        super(WoTThing, self).__init__(name, type_, description=description)
        self.property_fetching_coroutines = []

        # instantiate the WoT Properties by iterating through and executing the partial functions
        # associated with each
        for attribute_name in dir(self.__class__):
            if attribute_name.startswith('_'):
                continue
            if not isinstance(getattr(self.__class__, attribute_name), WoTProperty):
                continue
            wot_property_instance = getattr(self.__class__, attribute_name)
            logging.debug('creating property %s', wot_property_instance.name)
            wot_property_instance.wot_property_creation_function(self)
            try:
                self.property_fetching_coroutines.append(
                    wot_property_instance.property_fetching_coroutine
                )
            except AttributeError:  # no property is required to have a property_fetching_coroutine
                pass

    @classmethod
    def wot_property(
        kls,
        *,
        name,
        initial_value,
        description,
        value_source_fn=None,
        value_forwarder=None,
        **kwargs
    ):
        return WoTProperty(
            name=name,
            initial_value=initial_value,
            description=description,
            value_source_fn=value_source_fn,
            value_forwarder=value_forwarder,
            **kwargs
        )


class WoTServer(WebThingServer, RequiredConfig):
    required_config = Namespace()
    required_config.add_option(
        'service_port',
        doc='a port number for the Web Things Service',
        default=8888
    )

    def __init__(self, config, things, name=None, port=80, ssl_options=None):
        self.config = config

        if len(things) == 1:
            things = SingleThing(things[0])
        else:
            things = MultipleThings(things, name)

        super(WoTServer, self).__init__(things, port, ssl_options)
        self._set_of_all_thing_tasks = set()

    def add_task(self, a_task):
        self._set_of_all_thing_tasks.add(a_task)

    def _create_and_start_all_thing_tasks(self):
        # create the async polling tasks for each Thing's properties
        io_loop = get_event_loop()
        for a_thing in self.things.get_things():
            logging.debug(
                '    thing: %s with %s tasks',
                a_thing.name,
                len(a_thing.property_fetching_coroutines)
            )
            for a_coroutine in a_thing.property_fetching_coroutines:
                # bind the coroutine to its associated thing
                a_thing_coroutine = a_coroutine(a_thing)
                # create and schedule the Task for the coroutine
                a_thing_task = io_loop.create_task(a_thing_coroutine)
                self._set_of_all_thing_tasks.add(a_thing_task)
                logging.debug(
                    '        created task: %s.%s',
                    a_thing.name,
                    a_coroutine.property_name
                )

    def _cancel_and_stop_all_thing_tasks(self):
        # cancel all the thing_tasks en masse.
        pending_tasks_in_a_group = gather(
            *self._set_of_all_thing_tasks,
            return_exceptions=True
        )
        pending_tasks_in_a_group.cancel()
        # let the event loop run until the all the thing_tasks complete their cancelation
        logging.debug('shutting down all the things tasks')
        get_event_loop().run_until_complete(pending_tasks_in_a_group)

    def run(self):
        try:
            logging.debug('starting server {}'.format(self.name))
            self._create_and_start_all_thing_tasks()
            self.start()
        except KeyboardInterrupt:
            logging.debug('stop signal received')
            # when stopping the server, we need to halt any thing_tasks
            self._cancel_and_stop_all_thing_tasks()
            # finally stop the server
            self.stop()


logging_config = Namespace()
logging_config.add_option(
    'logging_level',
    doc='log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)',
    default='DEBUG',
    from_string_converter=lambda s: getattr(logging, s.upper(), None)
)
logging_config.add_option(
    'logging_format',
    doc='format string for logging',
    default='%(asctime)s %(filename)s:%(lineno)s %(levelname)s %(message)s',
)


def log_config(config, prefix=''):
    for key, value in config.items():
        if isinstance(value, Mapping):
            log_config(value, "{}.".format(key))
        else:
            logging.info('%s%s: %s', prefix, key, to_str(value))
