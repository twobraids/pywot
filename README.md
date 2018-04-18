# Python Web Thing Wrapper

The `webthing` module, associtated with the Things Gateway from Mozilla, is a
Python 3 module implementing the Web of Things (WoT) API.  It enables Python
modules to speak to systems that communicate via the WoT protocol.

The `webthing` module is written from a reference implementation written in
Javascript.  The style and idioms of Javascript are markedly different from
those in the Python world.  Working directly with `webthing` requires a shift
in thinking away from what would be a more common forms found in many Python
modules.

This `pywot` module wraps `webthing` in a more Pythonic interface.  This makes
for shorter, easier to read programs.

This project is an experiment.  It is meant as an educational tool giving an
example on how someone could make a full featured Web of Thing API for Python.
This project may not be maintained beyond my blog posts that use it as an example.

# directory structure
    /demo/ - several examples of the API
    /pywot/ - the code for pywot

# API Reference

## WoTThing
*class* pywot.**WoTThing**(config, name, type_, description)

An object derived from the base class `webthing.Thing` representing a device or virtual device. As a class, it provides services for further derived classes, focusing on reconciling `webthing.Properties` with the Python `property` method. Further derived classes may define Properties at class load time rather than during object initialization time. This facilitates modification of property values by simplifying the
syntax:
```python
# using the webthing API directly:
my_weather_station.get_thing().properties['temperature'].value.notify_of_external_update(32)
# the same thing using the pywot API
my_weather_station.temperature = 32
```
Derived classes also get an automatically generated asynchronous polling loop to fetch a value from some external source.
The derived class only needs to define an asynchronous method to fetch the value once and pass it to the 
`pywot.WoTThing.wot_property` classmethod when defining a property.

```python
class WeatherStation(pywot.WoTThing):

    async def get_weather_data(self):
        async with aiohttp.ClientSession() as session:
            async with async_timeout.timeout(config.seconds_for_timeout):
                async with session.get(config.target_url) as response:
                    self.weather_data = json.loads(await response.text())
        self.temperature = self.weather_data['current_observation']['temp_f']
    
    temperature = pywot.WoTThing.wot_property(
        'temperature',
        initial_value=0.0,
        description='the temperature in ℉',
        value_source_fn=get_weather_data,
        metadata={
            'units': '℉'
        }
    )
```
The `WoTThing` class requires configuration of only one value, the loop delay during polling.  That is supplied to the `__init__` method in the form `config.seconds_between_polling`.  This is library uses the `configman` package for propagating 
configuration from command-line, configuration files or the environment to object constructors.

Each instance of `pywot.WoTThing` requires a `name` and `description`, unrestricted strings.  The `type_` parameter is for a string from
the list at: https://iot.mozilla.org/wot/#web-thing-types, for most things that aren't switches or bulbs, 
'thing' is likely the best option.

## WoTThing.wot_property
pywot.WoTThing.**wot_property**(kls,
        *,
        name,
        initial_value,
        description,
        value_source_fn=None,
        value_forwarder=None,
        metadata=None
)

This classmethod works much like the Python `property` method.  It defines a `webthing.Property` for the enclosing derived class 
of `pywot.WoTThing`.  `name` and `description` are unrestricted strings.  `initial_value` will be used to both set the 
value and the type of the value for the property.  `value_source_fn` is a reference to an asynchronous method of the derived
class that will be periodically run to update the value of the property.  `None` means no polling is necessary for this 
property. `value_forwarder` is a reference to a function that will set a value to any underlying hardware when a new value 
is assigned to a property.  `metadata` is a Mapping of extra data that the UI can interpret use to help display or represent 
the value.  Possible values for the underlying 'webthing' API are unclear.


## WoTServer
*class* pywot.**WoTServer**(config, things, name=None, port=80, ssl_options=None)

This class derives from `pything.WebThingServer` and cooperates with the `pywot.Thing` class to provide a polling loop method
compatible with the underlying `tornado` Web server.  When the server's `run` method is executed, each `pywot.Thing` instance
gives its list of value updating tasks to the server.  The server then queues them all into the asynchronous event loop.  

`things` is an iterable of instances of `pywot.Thing`.  `name` is a unrestricted string.  `port` is the port onwhich to offer
HTTP services. `ssl_options` is unclear from the underlying `webthing` documentation.

## WoTServer.**run**
pywot.WoTServer.**run**()

This instance method of `pywot.WoTServer` handles starting and shutdown all the asynchronous value updating methods and 
the Web server.  It is a blocking call that can be terminated with the signal SIG_TERM or ^C from the command line.


## logging_config
pywot.**logging_config**

This is an instance of a `Namespace` object from the `configman` configuration system.  It holds configuration information
used to initialize the logging system.  It is offered as a convenience.  

## log_config
pywot.**log_config**

This is a module level method that will take an instance of completed `configman` compatible configuration and just stream
it out to logging at INFO level.  It is just a convenience if `configman` is employed in apps using this package.

