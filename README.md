# Python Web of Things Wrapper

The `webthing` module, associtated with the Things Gateway from Mozilla, is a
Python 3 module implementing the Web of Things (WoT) API.  It enables Python
modules to speak to systems that communicate via the WoT protocol.

The `webthing` module is written from a reference implementation written in
Javascript.  The style and idioms of Javascript are markedly different from
those in the Python world.  Working directly with `webthing` requires a shift
in thinking away from what would be considered Pythonic.

This `pywot` module wraps `webthing` in a more Pythonic interface.  This makes
for shorter, easier to read programs.
