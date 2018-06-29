#!/usr/bin/env python3
import json
import asyncio
import aiohttp
import async_timeout
import logging

# Demonstrate the Things API by controlling a light within the Things Gateway
# from outside the Things Gateway.  This code uses the Things Gateway RESTful API
# to control a set of Philips HUE bulbs.  The program uses transitions in color to mirror the
# real time phase and trend of the tide at a set of configurable locations.

from datetime import datetime
from configman import (
    Namespace,
    RequiredConfig,
    configuration
)
from pywot import (
    logging_config,
    log_config
)


async def get_tide_table(config, last_tide_in_the_past=None):
    # get the tide data from Weather Underground
    logging.info('loading new tide table')
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(config.seconds_for_timeout):
                    async with session.get(config.target_url) as response:
                        raw_tide_data = json.loads(await response.text())
                        break
        except Exception as e:
            logging.error('problem reading {}: {}'.format(config.target_url, e))
            logging.info('retrying after 20 second pause')
#             asyncio.sleep(20.0)
            raise

    # The raw tide data has junk in it that we don't want
    # Pare it down to just the High Tide and Low Tide events
    # ignoring all the other events that Weather Underground
    # gives in the tide data (sunset, sunrise, moonset, moonrise,
    # moon phase, ...)
    raw_tide_list = []
    try:
        for item in raw_tide_data["tide"]["tideSummary"]:
            if item["data"]["type"] in ("High Tide", "Low Tide"):
                raw_tide_list.append((
                    item["data"]["type"],
                    datetime(
                        int(item["utcdate"]["year"]),
                        int(item["utcdate"]["mon"]),
                        int(item["utcdate"]["mday"]),
                        int(item["utcdate"]["hour"]),
                        int(item["utcdate"]["min"]),
                    )
                ))
    except KeyError:
        logging.error(
            'Weather Underground is not currently supplying Tide data for this location'
        )
        raise Exception('Bad Location')
    if not len(raw_tide_list):
        logging.error(
            'Weather Underground is not currently supplying Tide data for this location'
        )
        raise Exception('Bad Location')

    # Now create a more useful list of tide events as tuples of
    # (TideType, TideTime, TimeToNextTide, StepTimeForNextTide
    future_tides_list = []
    for i, (tide_type_str, tide_datetime) in enumerate(raw_tide_list[:-1]):
        future_tides_list.append((
            tide_type_str,  # TideType
            tide_datetime,  # TideTime
            raw_tide_list[i + 1][1] - tide_datetime,  # TimeToNextTide
            (raw_tide_list[i + 1][1] - tide_datetime) / 120  # StepTimeForNextTide
        ))

    # We need the last tide event, but Weather Underground only gives us
    # future events.  Guess about timing of the previous tide was if it wasn't
    # already passed in to this method
    if last_tide_in_the_past is None:
        logging.debug('{}, {} no previous tide information, guessing...'.format(
                config.city_name,
                config.state_code,
        ))
        last_tide_in_the_past = (
            "Low Tide" if future_tides_list[0][0] == "High Tide" else "High Tide",
            future_tides_list[0][1] - future_tides_list[0][2],
            future_tides_list[0][2],
            future_tides_list[0][3],
        )

    # Create a tide table - a list of tide tuples where the first entry is the
    # most recent tide event in the past
    tide_table = [last_tide_in_the_past]
    tide_table.extend(future_tides_list)

    return tide_table


async def tide_iterator(config):
    # Create a never ending generator of high/low tide events
    tide_table = await get_tide_table(config)
    while True:
        for a_tide in tide_table:
            logging.info('{}, {} previous {} at {}UTC'.format(
                config.city_name,
                config.state_code,
                a_tide[0],
                a_tide[1]
            ))
            yield a_tide
        # we've exhausted the current tide table. Get the next one,
        # but preload it with the most recent tide event in the past
        tide_table = await get_tide_table(config, tide_table[-1])


# the colors to use in the transition from low tide to high tide
low_to_high_color_list = [
    '#00ff00', '#04ff00', '#08ff00', '#0cff00', '#10ff00', '#15ff00',
    '#19ff00', '#1dff00', '#21ff00', '#26ff00', '#2aff00', '#2eff00',
    '#32ff00', '#37ff00', '#3bff00', '#3fff00', '#43ff00', '#48ff00',
    '#4cff00', '#50ff00', '#54ff00', '#59ff00', '#5dff00', '#61ff00',
    '#65ff00', '#6aff00', '#6eff00', '#72ff00', '#76ff00', '#7bff00',
    '#7fff00', '#83ff00', '#88ff00', '#8cff00', '#90ff00', '#94ff00',
    '#99ff00', '#9dff00', '#a1ff00', '#a5ff00', '#aaff00', '#aeff00',
    '#b2ff00', '#b6ff00', '#bbff00', '#bfff00', '#c3ff00', '#c7ff00',
    '#ccff00', '#d0ff00', '#d4ff00', '#d8ff00', '#ddff00', '#e1ff00',
    '#e5ff00', '#e9ff00', '#eeff00', '#f2ff00', '#f6ff00', '#faff00',
    '#ffff00', '#fffa00', '#fff600', '#fff200', '#ffee00', '#ffe900',
    '#ffe500', '#ffe100', '#ffdd00', '#ffd800', '#ffd400', '#ffd000',
    '#ffcc00', '#ffc700', '#ffc300', '#ffbf00', '#ffbb00', '#ffb600',
    '#ffb200', '#ffae00', '#ffaa00', '#ffa500', '#ffa100', '#ff9d00',
    '#ff9900', '#ff9400', '#ff9000', '#ff8c00', '#ff8800', '#ff8300',
    '#ff7f00', '#ff7b00', '#ff7700', '#ff7200', '#ff6e00', '#ff6a00',
    '#ff6600', '#ff6100', '#ff5d00', '#ff5900', '#ff5400', '#ff5000',
    '#ff4c00', '#ff4800', '#ff4300', '#ff3f00', '#ff3b00', '#ff3700',
    '#ff3200', '#ff2e00', '#ff2a00', '#ff2600', '#ff2100', '#ff1d00',
    '#ff1900', '#ff1500', '#ff1000', '#ff0c00', '#ff0800', '#ff0400',
]

# the colors to use in the transition from high tide to low tide
high_to_low_color_list = [
    '#ff0000', '#ff0008', '#ff0010', '#ff0019', '#ff0022', '#ff002a',
    '#ff0033', '#ff003b', '#ff0043', '#ff004c', '#ff0054', '#ff005d',
    '#ff0066', '#ff006e', '#ff0077', '#ff007f', '#ff0087', '#ff0090',
    '#ff0098', '#ff00a1', '#ff00aa', '#ff00b2', '#ff00bb', '#ff00c3',
    '#ff00cb', '#ff00d4', '#ff00dc', '#ff00e5', '#ff00ee', '#ff00f6',
    '#ff00ff', '#f600ff', '#ee00ff', '#e500ff', '#dc00ff', '#d400ff',
    '#cb00ff', '#c300ff', '#bb00ff', '#b200ff', '#aa00ff', '#a100ff',
    '#9800ff', '#9000ff', '#8700ff', '#7f00ff', '#7700ff', '#6e00ff',
    '#6600ff', '#5d00ff', '#5400ff', '#4c00ff', '#4300ff', '#3b00ff',
    '#3300ff', '#2a00ff', '#2200ff', '#1900ff', '#1000ff', '#0800ff',
    '#0000ff', '#0008ff', '#0011ff', '#0019ff', '#0021ff', '#002aff',
    '#0033ff', '#003bff', '#0043ff', '#004cff', '#0055ff', '#005dff',
    '#0065ff', '#006eff', '#0077ff', '#007fff', '#0087ff', '#0090ff',
    '#0099ff', '#00a1ff', '#00a9ff', '#00b2ff', '#00bbff', '#00c3ff',
    '#00cbff', '#00d4ff', '#00ddff', '#00e5ff', '#00edff', '#00f6ff',
    '#00ffff', '#00fff6', '#00ffed', '#00ffe5', '#00ffdd', '#00ffd4',
    '#00ffcb', '#00ffc3', '#00ffbb', '#00ffb2', '#00ffa9', '#00ffa1',
    '#00ff99', '#00ff90', '#00ff87', '#00ff7f', '#00ff77', '#00ff6e',
    '#00ff65', '#00ff5d', '#00ff55', '#00ff4c', '#00ff43', '#00ff3b',
    '#00ff33', '#00ff2a', '#00ff21', '#00ff19', '#00ff11', '#00ff08',
]


async def change_bulb_color(config, a_color):
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(config.seconds_for_timeout):
                    async with session.put(
                        "http://gateway.local/things/{}/properties/color".format(config.thing_id),
                        headers={
                            'Accept': 'application/json',
                            'Authorization': 'Bearer {}'.format(config.things_gateway_auth_key),
                            'Content-Type': 'application/json'
                        },
                        data='{{"color": "{}"}}'.format(a_color)
                    ) as response:
                        return await response.text()
        except aiohttp.client_exceptions.ClientConnectorError as e:
            logging.error('problem contacting http:/gateway.local: {}'.format(e))
            logging.info('retrying after 20 second pause')
            asyncio.sleep(20.0)


async def control_tide_light(config):
    # loop over all the tide events

    async for a_tide in tide_iterator(config):
        step_time = a_tide[1]
        if a_tide[0] == "Low Tide":
            a_color_list = low_to_high_color_list
            logging.debug('{}, {} using low to high color set'.format(
                config.city_name,
                config.state_code
            ))
        else:
            a_color_list = high_to_low_color_list
            logging.debug('{}, {} using high to low color set'.format(
                config.city_name,
                config.state_code
            ))
        # divide the time between the last tide in the past with the
        # next tide in the future into 120 time segments: one color for each
        for step in range(120):
            now = datetime.utcnow()
            if now > step_time:
                # if we're ahead of the correct time, for example, during initial
                # startup when not perfectly aligned with the most recent tide,
                # increment the step_time, but skip setting the tide light color
                # and waiting.  This fast forwards the loop to the current time,
                # synchronizing with the correct color for the current time.
                step_time += a_tide[3]
                continue
            logging.debug("{}, {} step:{}UTC wait:{}".format(
                config.city_name,
                config.state_code,
                step_time, a_tide[3]
            ))
            logging.info("{}, {} setting color: {}".format(
                config.city_name,
                config.state_code,
                a_color_list[step]
            ))
            await change_bulb_color(config, a_color_list[step])
            await asyncio.sleep(a_tide[3].seconds)
            step_time += a_tide[3]


async def run_all_tide_lights(config):
    # invoke all the tide lights by marrying the control_tide_light coroutine
    # with the appropriate part of the configuration for each tide light.
    # This creates a list of coroutine objects to be gathered and executed.
    tide_light_coroutines = [
        control_tide_light(config[a_tide_light_namespace_name])
        for a_tide_light_namespace_name in config.tide_light_name_list
    ]
    await asyncio.gather(*tide_light_coroutines)


# The following section defines a structured configuration document in the form
# a nested Mapping of configuration keys to configuration values.  Each entry
# contains a name, documentation string, a default value, plus other optional
# components. This will servce to define command-line arguments, and the structure
# of configuration files.

# This program can run many tide lights at the same time.  This namespace represents
# the configuration data required for each unique tide light: location and
# the id of the bulb to control
tide_light_config = Namespace()
tide_light_config.add_option(
    'state_code',
    doc='the two letter state code',
    default="OR",
)
tide_light_config.add_option(
    'city_name',
    doc='the name of the city',
    default="Waldport",
)
tide_light_config.add_option(
    'thing_id',
    doc='the id of the color bulb to control',
    default="TIDE LIGHT THING ID"
)


# this defines a constant based solely on configuration data
def create_url(config, local_namespace, args):
    """generate a URL to fetch local weather data from Weather Underground using
    configuration data"""
    return "http://api.wunderground.com/api/{}/tide/q/{}/{}.json".format(
        local_namespace.weather_underground_api_key,
        local_namespace.state_code,
        local_namespace.city_name
    )


tide_light_config.add_aggregation(
    'target_url',
    function=create_url
)

# these are the common configuration parameters that will be used for all tide
# lights.
base_required_config = Namespace()
base_required_config.add_option(
    'weather_underground_api_key',
    doc='the api key to access Weather Underground data',
    short_form="K",
    default="WEATHER UNDERGROUND ACCESS KEY"
)
base_required_config.add_option(
    'things_gateway_auth_key',
    doc='the api key to access the Things Gateway',
    short_form="G",
    default='THINGS GATEWAY AUTH KEY',
)
base_required_config.add_option(
    'seconds_for_timeout',
    doc='the number of seconds to allow for fetching tide data',
    default=10
)


# this is a configman helper function that creates the configuration
# structure for the number of tide lights requested.  It creates a new namespace
# for each requested bulb and puts the tide_light_config into each one.  It
# encapsulates the namespaces into an instance of an object called TideLightCollection.
# This object has a class attribute called required_config.  Configman
# will automatically use that to fill out another layer of the structured
# configuration document.
def tide_config_setup(number_of_tide_lights):
    class TideLightCollection(RequiredConfig):
        required_config = Namespace()
        required_config.add_aggregation(
            name='tide_light_name_list',
            function=lambda c, l, a: TideLightCollection.tide_light_name_list
        )
        tide_light_name_list = []
        for tide_light_index in range(int(number_of_tide_lights)):
            namespace_name_for_index = 'tide{}'.format(tide_light_index)
            tide_light_name_list.append(namespace_name_for_index)
            required_config[namespace_name_for_index] = Namespace()
            required_config[namespace_name_for_index].update(tide_light_config)

        def __repr__(self):
            return number_of_tide_lights

    return TideLightCollection()


# the definition of the number_of_tide_lights config parameter says that the function
# tide_config_setup should be used to convert any text input (from command line or
# config files) into the collection of nested namespaces representing each individual
# tide light.
base_required_config.add_option(
    'number_of_tide_lights',
    doc='how many tide lights to set up',
    default="1",
    short_form="n",
    from_string_converter=tide_config_setup
)
base_required_config.update(logging_config)


if __name__ == '__main__':

    config = configuration([base_required_config])
    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format
    )
    log_config(config)

    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(run_all_tide_lights(config))
