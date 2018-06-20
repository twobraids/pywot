#!/usr/bin/env python3
import json
import math
import asyncio
import aiohttp
import async_timeout
from datetime import (
    datetime,
    timedelta
)



async def get_tide_table(last_tide=None):
    async with aiohttp.ClientSession() as session:
        async with async_timeout.timeout(10):
            async with session.get(
                "http://api.wunderground.com/api/c5410a6a36d2e304/tide/q/OR/waldport.json",
            ) as response:
                raw_tide_data = json.loads(await response.text())

    raw_future_tides = []
    for item in raw_tide_data["tide"]["tideSummary"]:
        if item["data"]["type"] in ("High Tide", "Low Tide"):
            raw_future_tides.append((
                item["data"]["type"],
                datetime(
                    int(item["date"]["year"]),
                    int(item["date"]["mon"]),
                    int(item["date"]["mday"]),
                    int(item["date"]["hour"]),
                    int(item["date"]["min"]),
                )
            ))

    future_tides = []
    #for i, (x, t) in enumerate(raw_future_tides[:-1]):  #TODO
    for i, (x, t) in enumerate(raw_future_tides[:2]):
        future_tides.append((
            # 0 - tide type
            x,
            # 1 - tide time
            t,
            # 2 - length of tide
            raw_future_tides[i + 1][1] - t,
            # 3 - time between tides
            (raw_future_tides[i + 1][1] - t) / 120
        ))

    if last_tide == None:
        last_tide = (
            "Low Tide" if future_tides[0][0] == "High Tide" else "High Tide",
                future_tides[0][1] - future_tides[0][2],
                future_tides[0][2],
                future_tides[0][3],
        )
    tide_table = [last_tide]

    tide_table.extend(future_tides)
    return tide_table

async def tide_stream():
    tide_table = await get_tide_table()
    while True:
        for a_tide in tide_table:
            yield a_tide
        tide_table = await get_tide_table(tide_table[-1])


def hsv2rgb(h, s, v):
    h = float(h)
    s = float(s)
    v = float(v)
    h60 = h / 60.0
    h60f = math.floor(h60)
    hi = int(h60f) % 6
    f = h60 - h60f
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    r, g, b = 0, 0, 0
    if hi == 0: r, g, b = v, t, p
    elif hi == 1: r, g, b = q, v, p
    elif hi == 2: r, g, b = p, v, t
    elif hi == 3: r, g, b = p, q, v
    elif hi == 4: r, g, b = t, p, v
    elif hi == 5: r, g, b = v, p, q
    r, g, b = int(r * 255), int(g * 255), int(b * 255)
    return r, g, b

def rgb2hex(r, g, b):
    return "#{0:02x}{1:02x}{2:02x}".format(r, g, b)

async def control_tide():
    low_to_high = [rgb2hex(*hsv2rgb(x, 1.0, 1.0)) for x in range(120, 0, -1)]
    high_to_low = [rgb2hex(*hsv2rgb(x, 1.0, 1.0)) for x in range(360, 120, -2)]

    async for a_tide in tide_stream():
        step_time = a_tide[1]
        print ('next ', step_time)
        for step in range(120):
            colors = low_to_high if a_tide[0] == "Low Tide" else high_to_low
            now = datetime.now()
            if now > step_time:
                step_time += a_tide[3]
                print (now, step_time)
                continue
            print("now: {}  step:{}  next:{}".format(now, step_time, a_tide[1]))
            print("set ", colors[step])
            print("wait ", a_tide[3].seconds)
            await put_tide_color(colors[step])
            await asyncio.sleep(a_tide[3].seconds)
            step_time += a_tide[3]


async def put_tide_color(a_color):
    async with aiohttp.ClientSession() as session:
        async with async_timeout.timeout(10):
            async with session.put(
                "http://gateway.local/things/zb-0017880103415d70/properties/color",
                headers={
                    'Accept': 'application/json',
                    'Authorization': 'Bearer eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImRjYTVkMTQ0LTBkNjAtNDkzYS1iMDU0LWI1NGM0NzBjZDRhYyJ9.eyJjbGllbnRfaWQiOiJsb2NhbC10b2tlbiIsInJvbGUiOiJhY2Nlc3NfdG9rZW4iLCJzY29wZSI6Ii90aGluZ3M6cmVhZHdyaXRlIiwiaWF0IjoxNTI5NDM3MjE1fQ.dUp15a2Qyu6PeaXZYozpySfxkl_gZOsbaDtuzX-6aEY5vVw78H5OKFQIqbnGvmRvPyBHK1xfSMlq4FKxRmfusA',
                    'Content-Type': 'application/json'
                },
                data='{{"color": "{}"}}'.format(a_color)
            ) as response:
                return await response.text()

async def main():
    await control_tide()


if __name__ == '__main__':
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(main())
