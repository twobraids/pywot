import logging
import asyncio
import astral

from datetime import (
    timedelta,
    datetime,
)


class RuleTrigger:
    def __init__(self, config, name):
        self.config = config
        self.name = name
        self.rules_that_use_this_thing = []
        self.canceled = False

    def _apply_rules(self, a_property_name=None, a_value=None):
        if self.canceled is False:
            for a_rule in self.rules_that_use_this_thing:
                a_rule.action(self, a_property_name, a_value)


class TimeBasedTrigger(RuleTrigger):
    scale = {"S": 1, "M": 60, "H": 60 * 60, "D": 60 * 60 * 24}

    def __init__(self, config, name):
        super(TimeBasedTrigger, self).__init__(config, name)
        self.system_timezone = config.system_timezone
        self.local_timezone = config.local_timezone

    @staticmethod
    def time_difference_in_seconds(start_time, end_time):
        # both as datetime.time objects
        s_time = datetime(1900, 1, 1, start_time.hour, start_time.minute, start_time.second)
        e_time = datetime(1900, 1, 1, end_time.hour, end_time.minute, end_time.second)
        if e_time > s_time:
            e_time = e_time + timedelta(1)
        difference = s_time - e_time
        return difference.total_seconds()

    @staticmethod
    def duration_str_to_seconds(duration_str):
        duration_str = str(duration_str)  # allows ints to be passed in
        duration_str = duration_str.strip()
        units = "S"
        if duration_str[-1] in ("HhMmSsDd"):
            units = duration_str[-1].upper()
            duration_str = duration_str[:-1]
        return int(duration_str) * TimeBasedTrigger.scale[units]

    def local_now(self):
        if self.local_timezone is self.system_timezone:
            return self.local_timezone.localize(datetime.now())
        system_now = self.system_timezone.localize(datetime.now())
        return system_now.astimezone(self.local_timezone)

    def now_in_timezone(self, target_timezone):
        system_now = self.system_timezone.localize(datetime.now())
        return system_now.astimezone(target_timezone)


class HeartBeat(TimeBasedTrigger):
    def __init__(
        self,
        config,
        name,
        period_str
        # duration should be a integer in string form with an optional
        #    H, h, M, m, S, s, D, d  as a suffix to indicate units - default S
    ):
        super(HeartBeat, self).__init__(config, name)
        self.period = self.duration_str_to_seconds(period_str)

    async def trigger_detection_loop(self):
        logging.debug("Starting heartbeat timer %s", self.period)
        while True:
            logging.info("%s beats", self.name)
            self._apply_rules()
            await asyncio.sleep(self.period)


class DelayTimer(TimeBasedTrigger):
    def __init__(
        self,
        config,
        name,
        timer_period_str,
        # timer_period_str and  period_off_str should be a integer in string form
        # with an optional H, h, M, m, S, s, D, d  as a suffix to indicate units
        # default is S
    ):
        super(DelayTimer, self).__init__(config, name)
        self.original_timer_period_str = timer_period_str
        self.timer_period_in_seconds = self.duration_str_to_seconds(timer_period_str)
        self.delay_timers = []
        self.suppress_cancel = False

    @property
    def is_not_running(self):
        try:
            return self.timer_task.done()
        except AttributeError:
            return True

    @property
    def is_running(self):
        try:
            return not self.timer_task.done()
        except AttributeError:
            return False

    async def _start_timer(self):
        try:
            while len(self.delay_timers) > 0:
                await asyncio.sleep(self.delay_timers.pop())
            self.suppress_cancel = True
            self._apply_rules("timer_status", False)

        except asyncio.CancelledError:
            logging.info("%s timer canceled", self.name)
        finally:
            logging.info("%s timer done", self.name)
            self.suppress_cancel = False

    def ensure_the_timer_is_running(self):
        if self.is_not_running:
            self.timer_task = asyncio.ensure_future(self._start_timer())

    def add_time(self):
        logging.debug("%s adding %ss", self.name, self.timer_period_in_seconds)
        self.delay_timers.append(self.timer_period_in_seconds)
        self.ensure_the_timer_is_running()

    def cancel(self):
        logging.info("a cancel request has been made")
        if self.is_running and not self.suppress_cancel:
            logging.info("%s cancel request", self.name)
            self.delay_timers = []
            self.timer_task.cancel()
            self.timer_task = None
        else:
            logging.info("cancel request rejected")


class DurationTimer(TimeBasedTrigger):
    def __init__(
        self,
        config,
        name,
        on_period_in_seconds_str,
        off_period_in_seconds_str="0",
        # period_on_str and  period_off_str should be a integer in string form
        # with an optional H, h, M, m, S, s, D, d  as a suffix to indicate units
        # default is S
        max_repeats=1,
    ):
        super(DurationTimer, self).__init__(config, name)
        self.on_period_in_seconds = self.duration_str_to_seconds(on_period_in_seconds_str)
        self.off_period_in_seconds = self.duration_str_to_seconds(off_period_in_seconds_str)
        self.max_repeats = max_repeats
        self.output_state = False

    @property
    def is_not_running(self):
        try:
            return self.timer_task.done()
        except AttributeError:
            return True

    @property
    def is_running(self):
        try:
            return not self.timer_task.done()
        except AttributeError:
            return False

    def set_state_and_apply_rules(self, output_state):
        try:
            self.output_state = output_state
            logging.info("%s output_state, %s", self.name, output_state)
            self._apply_rules("output_state", output_state)
        except Exception as e:
            logging.error(e)
            raise

    async def _start_timer(self):
        repeat_counter = 1
        try:
            while True:
                self.set_state_and_apply_rules(True)
                logging.info("%s sleeping for %ss", self.name, self.on_period_in_seconds)
                await asyncio.sleep(self.on_period_in_seconds)
                self.set_state_and_apply_rules(False)
                if self.max_repeats <= repeat_counter:
                    break
                repeat_counter += 1
                logging.info("%s sleeping for %ss", self.name, self.off_period_in_seconds)
                await asyncio.sleep(self.off_period_in_seconds)

            self._apply_rules("timer_status", False)

        except asyncio.CancelledError:
            logging.info("% timer canceled", self.name)
        finally:
            logging.info("%s timer done", self.name)

    def start_timer(self):
        logging.info("the timer has started")
        self.timer_task = asyncio.ensure_future(self._start_timer())

    def cancel(self):
        logging.info("%s cancel request", self.name)
        if self.is_running:
            logging.info("%s doing cancel", self.name)
            self.timer_task.cancel()


class AbsoluteTimeTrigger(TimeBasedTrigger):
    def __init__(
        self,
        config,
        name,
        # time_of_day_str should be in the 24Hr form "HH:MM:SS"
        time_of_day_str,
    ):
        super(AbsoluteTimeTrigger, self).__init__(config, name)
        self.trigger_time = datetime.strptime(time_of_day_str, "%H:%M:%S").time()

    async def trigger_detection_loop(self):
        logging.debug("Starting timer %s", self.trigger_time)
        while True:
            time_until_trigger_in_seconds = self.time_difference_in_seconds(
                self.trigger_time, self.local_now().time()
            )
            logging.debug("timer triggers in %sS", time_until_trigger_in_seconds)
            await asyncio.sleep(time_until_trigger_in_seconds)
            self._apply_rules("activated", True)
            await asyncio.sleep(1)


class DailySolarEventsTrigger(TimeBasedTrigger):
    def __init__(
        self,
        config,
        name,
        # list of any daily events (see self.all_possible_event_names)
        event_name_list,
        lat_long_tuple,
        timezone_name,  # like "US/Pacific" or "UTC"
        elevation_in_meters,
        # modify the event time - should be a signed integer in string form with an
        # optional H, h, M, m, S, s, D, d  as a suffix to indicate units
        # default is S
        offset="0s",
    ):
        super(DailySolarEventsTrigger, self).__init__(config, name)
        self.event_name_list = event_name_list
        self.location = astral.Location(
            (
                "location_name",
                "location_region",
                lat_long_tuple[0],
                lat_long_tuple[1],
                timezone_name,
                elevation_in_meters,
            )
        )
        self.offset = timedelta(0, self.duration_str_to_seconds(offset))
        self.one_day = timedelta(1)
        self.all_possible_event_names = (
            "blue_hour_start",
            "blue_hour_end",
            "dawn",
            "daylight_start",
            "daylight_end",
            "dusk",
            "golden_hour_start",
            "golden_hour_end",
            "night_start",
            "night_end",
            "rahukaalam_start",
            "rahukaalam_end",
            "solar_midnight",
            "solar_noon",
            "sunrise",
            "sunset",
            "twilight_start",
            "twilight_end",
        )

    def get_schedule(self):
        event_list = []
        for an_event_name in self.event_name_list:
            if an_event_name not in self.all_possible_event_names:
                error_message = "{}  is not a valid event name".format(an_event_name)
                logging.error(error_message)
                continue

            base_event_name = an_event_name.replace("_end", "").replace("_start", "")
            try:
                event = getattr(self.location, base_event_name)()
            except Exception as e:
                # astral will raise exceptions if any of the sun events
                # cannot be calculated for a particular day - for example, there are high latitude
                # places where the time-delta between sunrise and sunset is measured in days.  Not
                # every day gets a sunrise or sunset.
                logging.error(e)
                continue

            if isinstance(event, datetime):
                event_list.append((event + self.offset, an_event_name))
                continue

            if isinstance(event, tuple):
                # the tuples are all (start_datetime, end_datetime) except for
                # the 'night' event where they are returned as (end_datetime, start_datetime)
                index = 0 if an_event_name.endswith("_start") else 1
                if base_event_name == "night":
                    event = (event[1], event[0])
                event_list.append((event[index] + self.offset, an_event_name))
                continue
        return event_list

    async def trigger_event(self, now, time_delta, event_name):
        logging.info(
            "%s in %s seconds (%s)", event_name, time_delta.total_seconds(), now + time_delta
        )
        await asyncio.sleep(time_delta.total_seconds())
        self._apply_rules(event_name)

    async def trigger_detection_loop(self):
        while True:
            event_schedule = self.get_schedule()
            for event_datetime, event_name in event_schedule:
                now = self.now_in_timezone(self.location.tz)
                if event_datetime < now:
                    continue
                time_delta = event_datetime - now
                logging.info("new schedule %s in %s (%s)", event_name, time_delta, event_datetime)
                asyncio.ensure_future(self.trigger_event(now, time_delta, event_name))

            now = self.now_in_timezone(self.location.tz)
            next_day = (now + self.one_day).date()

            next_schedule_time = self.local_timezone.localize(
                datetime(next_day.year, next_day.month, next_day.day, 1)  # next day at 1am
            )
            time_interval_until_next_schedule = next_schedule_time - now
            logging.info(
                "%s: next day's schedule pulled in %s seconds (%s))",
                self.name,
                time_interval_until_next_schedule.total_seconds(),
                next_schedule_time,
            )

            await asyncio.sleep(time_interval_until_next_schedule.total_seconds())
