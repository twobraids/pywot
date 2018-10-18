import logging
import asyncio
import astral

from datetime import (
    timedelta,
    datetime,
)


class RuleTrigger():
    def __init__(self, config, name):
        self.config = config
        self.name = name
        self.participating_rules = []
        self.canceled = False

    def _apply_rules(self, a_property_name=None, a_value=None):
        if self.canceled is False:
            for a_rule in self.participating_rules:
                a_rule.action(self, a_property_name, a_value)


class TimeBasedTrigger(RuleTrigger):
    scale = {
        'S': 1,
        'M': 60,
        'H': 60 * 60,
        'D': 60 * 60 * 24
    }

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
        return difference.seconds

    @staticmethod
    def duration_str_to_seconds(duration_str):
        duration_str = str(duration_str)  # allows ints to be passed in
        duration_str = duration_str.strip()
        units = 'S'
        if duration_str[-1] in ('HhMmSsDd'):
            units = duration_str[-1].upper()
            duration_str = duration_str[:-1]
        return int(duration_str) * TimeBasedTrigger.scale[units]

    def local_now(self):
        if self.local_timezone is self.system_timezone:
            return self.local_timezone.localize(datetime.now())
        system_now = self.system_timezone.localize(datetime.now())
        return system_now.astimezone(self.local_timezone)


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
        logging.debug('Starting heartbeat timer %s', self.period)
        while True:
            logging.info('%s beats', self.name)
            self._apply_rules()
            await asyncio.sleep(self.period)


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
        max_repeats=1
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
            logging.info(
                '%s output_state, %s',
                self.name,
                output_state
            )
            self._apply_rules('output_state', output_state)
        except Exception as e:
            logging.error(e)
            raise

    async def _start_timer(self):
        repeat_counter = 1
        try:
            while True:
                self.set_state_and_apply_rules(True)
                logging.info('%s sleeping for %ss', self.name, self.on_period_in_seconds)
                await asyncio.sleep(self.on_period_in_seconds)
                self.set_state_and_apply_rules(False)
                if self.max_repeats <= repeat_counter:
                    break
                repeat_counter += 1
                logging.info('%s sleeping for %ss', self.name, self.off_period_in_seconds)
                await asyncio.sleep(self.off_period_in_seconds)

            self._apply_rules('timer_status', False)

        finally:
            logging.info('%s timer done', self.name)

    def start_timer(self):
        logging.info('the timer has started')
        self.timer_task = asyncio.ensure_future(self._start_timer())

    def cancel(self):
        logging.info('%s cancel request', self.name)
        if self.is_running:
            logging.info('%s doing cancel', self.name)
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
        self.trigger_time = datetime.strptime(time_of_day_str, '%H:%M:%S').time()

    async def trigger_detection_loop(self):
        logging.debug('Starting timer %s', self.trigger_time)
        while True:
            time_until_trigger_in_seconds = self.time_difference_in_seconds(
                self.trigger_time,
                self.local_now().time()
            )
            logging.debug('timer triggers in %sS', time_until_trigger_in_seconds)
            await asyncio.sleep(time_until_trigger_in_seconds)
            self._apply_rules('activated', True)
            await asyncio.sleep(1)


class SunTrigger(TimeBasedTrigger):
    def __init__(
        self,
        config,
        name,
        sun_event_name,  # dawn, sunrise, noon, sunset, dusk
        lat_long_tuple,
        timezone_name,  # like "US/Pacific" or "GMT"
        elevation_in_meters,
        time_offset_in_seconds=0
    ):
        super(SunTrigger, self).__init__(config, name)
        self.sun_event_name = sun_event_name
        self.location = astral.Location((
            "location_name",
            "location_region",
            lat_long_tuple[0],
            lat_long_tuple[1],
            timezone_name,
            elevation_in_meters
        ))
        self.time_offset = timedelta(0, time_offset_in_seconds)
        self.one_day = timedelta(1)

    def get_sun_schedule(self, now):
        try:
            return self.location.sun(now)
        except Exception:
            # astral will raise exceptions if any of the sun events
            # cannot be calculated - for example there is no sunrise
            # in midwinter or sunset in mid summer in some locations.
            # Guess by returning now + one day
            return {self.sun_event_name: now + self.one_day}

    async def trigger_detection_loop(self):
        while True:
            now = self.local_now().astimezone(self.location.tz)
            sun_schedule = self.get_sun_schedule(now)
            if sun_schedule[self.sun_event_name] + self.time_offset < now:
                # this event is in the past, get tomorrow's event instead
                sun_schedule = self.get_sun_schedule(now + self.one_day)

            time_until_trigger_in_seconds = self.time_difference_in_seconds(
                sun_schedule[self.sun_event_name] + self.time_offset,
                now
            )
            logging.debug('timer triggers in %sS', time_until_trigger_in_seconds)
            await asyncio.sleep(time_until_trigger_in_seconds)
            self._apply_rules('activated', True)
            await asyncio.sleep(1)
