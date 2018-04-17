# Python Web of Things Wrapper

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

*class* pywot.**WoTThing**(config, name, type_, description)

a Thing object derived from the base class `webthing` representing a device or virtual device. As a class, it provides services for further derived classes, focusing on reconciling `webthing.Properties` with the Python `property` method. Further derived classes may define Properties at class load time rather than during object initialization time. This facilitates modification of property values by simplifying the
syntax:
```python
my_weather_station.temperature = 32
# instead of using the webthing.Thing API directly:
my_weather_station.get_thing().get_property('temperature').value.notify_of_external_update(32)
```


