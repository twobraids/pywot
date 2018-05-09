from webthing import (
    Thing,
    Property,
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
    }[type(example_value)]


def create_wot_property(
    thing_instance,
    *,
    name,
    initial_value,
    description,
    value_source_fn=None,
    value_forwarder=None,
    **kwargs
):
    """Is effectively an unbound method of the WoTThing class.  It is used to add a new Thing
    Property to an intializing instance of a WoTThing."""
    if value_forwarder is None:
        value = Value(initial_value)
    else:
        value = Value(initial_value, value_forwarder=partial(value_forwarder, thing_instance))
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
        # instantiate the WoT Properties by iterating through and executing the partial functions
        # associated with each
        for property_name, create_wot_property_fn in self.wot_property_functions.items():
            logging.debug('creating property %s', property_name)
            create_wot_property_fn(self)

    # a mapping of property names to partials of the `create_wot_property` method above
    wot_property_functions = {}
    # a list of asynchronous methods that can fetch values for each of the properties from
    # whatever underlying (virtual) mechanism embodies the semantic meaning of the properties
    property_fetching_coroutines = []

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
        # WoT Properties must be instantiated when the Thing is instantiated.  Since this code runs
        # at class load time, we must just save the parameters for a future instantiation.  We do
        # this with a partial of the `create_wot_property` and save it in the mapping keyed by
        # Wot Property names.
        kls.wot_property_functions[name] = partial(
            create_wot_property,
            name=name,
            initial_value=initial_value,
            description=description,
            value_source_fn=value_source_fn,
            value_forwarder=value_forwarder,
            **kwargs
        )
        if value_source_fn is not None:
            # since this Wot Property has its own function for a source of values, it will need an
            # async loop to poll for the values.  We define it here as a closure over that
            # the `value_source_fn`.  Since it will be executed only after instantiation
            # and the first parameter is an instance of Thing, we're effectively making a new
            # instance method.  We save the closure function in the `property_fetching_coroutines`
            # list.
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
            kls.property_fetching_coroutines.append(a_property_fetching_coroutine)

        # Finally, we make a getter and setter for the WoT Property so that we can access
        # and modify the value of the property using normal Python property syntax.
        # These two functions are closures over the name of the WoT Property.
        def get_value_fn(thing_instance):
            return thing_instance.properties[name].value.get()

        def set_value_fn(thing_instance, new_value):
            thing_instance.properties[name].value.notify_of_external_update(new_value)

        # wrap the getter and setter into a standard Python property and return it
        return property(get_value_fn, set_value_fn)


class WoTServer(WebThingServer, RequiredConfig):
    required_config = Namespace()
    required_config.add_option(
        'service_port',
        doc='a port number for the Web Things Service',
        default=8888
    )

    def __init__(self, config, things, name=None, port=80, ssl_options=None):
        self.config = config
        super(WoTServer, self).__init__(things, name, port, ssl_options)
        self._set_of_all_thing_tasks = set()

    def add_task(self, a_task):
        self._set_of_all_thing_tasks.add(a_task)

    def _create_and_start_all_thing_tasks(self):
        # create the async polling tasks for each Thing's properties
        io_loop = get_event_loop()
        for a_thing in self.things:
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
