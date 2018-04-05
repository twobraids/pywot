from webthing import (
    Thing,
    Property,
    Value,
    WebThingServer,
)

from asyncio import (
    Task,
    sleep,
    gather
)
from tornado.ioloop import (
    IOLoop
)

from functools import partial

from configman import (
    Namespace,
    RequiredConfig
)
from collections import (
    Mapping
)
import logging


def pytype_as_wottype(example_value):
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
    ui_setter=None,
    metadata=None
):
    value = Value(initial_value, setter=ui_setter)
    property_metadata = {
        "type": pytype_as_wottype(initial_value),
        "description": description,
    }
    if metadata:
        property_metadata.update(metadata)
    logging.debug(thing_instance)
    thing_instance.add_property(
        Property(
            thing_instance,
            name,
            value,
            property_metadata
        )
    )


class WoTThing(Thing, RequiredConfig):
    required_config = Namespace()
    required_config.add_option(
        'seconds_between_polling',
        doc='the number of seconds between each time polling',
        default=120
    )

    def __init__(self, config, name, description):
        self.config = config
        super(WoTThing, self).__init__(name, description=description)
        for property_name, create_wot_property_fn in self.class_properties_as_partial.items():
            logging.debug('creating property %s', property_name)
            create_wot_property_fn(self)

    class_properties_as_partial = {}
    class_property_tasks = []

    @classmethod
    def wot_property(
        kls,
        *,
        name,
        initial_value,
        description,
        value_source_fn=None,
        ui_setter=None,
        metadata=None
    ):
        # we cannot instantiate the Property yet, just save the parameters in the form of a partial
        kls.class_properties_as_partial[name] = partial(
            create_wot_property,
            name=name,
            initial_value=initial_value,
            description=description,
            value_source_fn=value_source_fn,
            ui_setter=ui_setter,
            metadata=metadata
        )
        if value_source_fn is not None:
            # this property will require a polling loop to fetch new values
            async def property_value_task(thing_instance):
                while True:
                    await value_source_fn(thing_instance)
                    await sleep(thing_instance.config.seconds_between_polling)
            property_value_task.property_name = name
            print('setup task {}'.format(name))
            kls.class_property_tasks.append(property_value_task)
        # to allow the thing to access and change its own property

        def get_value_fn(thing_instance):
            return thing_instance.properties[name].value.get()

        def set_value_fn(thing_instance, new_value):
            thing_instance.properties[name].value.notify_of_external_update(new_value)

        return property(get_value_fn, set_value_fn)


def log_config(config, prefix=''):
    for key, value in config.items():
        if isinstance(value, Mapping):
            log_config(value, "{}.".format(key))
        else:
            logging.info('%s%s: %s', prefix, key, value)


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

    def run(self):
        try:
            io_loop = IOLoop.current().asyncio_loop
            for a_thing in self.things:
                logging.debug('thing: %s with %s tasks', a_thing.name, len(a_thing.class_property_tasks))
                for a_task in a_thing.class_property_tasks:
                    io_loop.create_task(a_task(a_thing))
                    logging.debug('created task: %s.%s', a_thing.name, a_task.property_name)
            logging.debug('server.start')
            self.start()
        except KeyboardInterrupt:
            logging.debug('stop signal received')
            # when stopping the server, we need to halt any tasks pending from the
            # method 'monitor_router'. Gather them together and cancel them en masse.
            pending_tasks_in_a_group = gather(*Task.all_tasks(), return_exceptions=True)
            pending_tasks_in_a_group.cancel()
            # let the io_loop run until the all the tasks complete their cancelation
            io_loop.run_until_complete(pending_tasks_in_a_group)
            # finally stop the server
            self.stop()
