import logging
import asyncio


from datetime import (
    timedelta,
    datetime,
)


class RuleTrigger():
    def __init__(self, name):
        self.name = name
        self.participating_rules = []

    def _apply_rules(self, a_property_name, a_value):
        for a_rule in self.participating_rules:
            a_rule.action(self, a_property_name, a_value)


class TimeBasedTrigger(RuleTrigger):
    scale = {
        'S': 1,
        'M': 60,
        'H': 60 * 60,
        'D': 60 * 60 * 24
    }

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
    def duration_str_to_int(duration_str):
        duration_str = str(duration_str)  # allows ints to be passed in
        duration_str = duration_str.strip()
        units = 'S'
        if duration_str[-1] in ('HhMmSsDd'):
            units = duration_str[-1].upper()
            duration_str = duration_str[:-1]
        return int(duration_str) * TimeBasedTrigger.scale[units]


class AbsoluteTimeTrigger(TimeBasedTrigger):
    """This device will work as a rule trigger at a set time each day.  It optionally has a duration
    that will trigger when the duration ends after the set time.  It has another option to repeat
    the trigger and duration a set number of times after the initial absolute time trigger."""

    def __init__(
        self,
        name,
        # time_of_day_str should be in the 24Hr form "HH:MM:SS"
        time_of_day_str,
        # duration & repeat should be a integer in string form with an optional
        #    H, h, M, m, S, s, D, d  as a suffix to indicate units - default S
        duration_str="60",
        repeat_every_str="0",
        max_repeats=0
    ):
        super(AbsoluteTimeTrigger, self).__init__(name)
        # when 'activated' is True, the absolute time trigger has been activated and the
        # asynchronous monitor_state method is running
        self.activated = False
        # when 'triggered' is True, time is within the duration specified within 'duration'
        self.triggered = False

        self.trigger_time = datetime.strptime(time_of_day_str, '%H:%M:%S').time()
        self.duration = self.duration_str_to_int(duration_str)
        self.repeat_every = self.duration_str_to_int(repeat_every_str)
        self.max_repeats = max_repeats

    async def monitor_state(self):
        logging.debug('Starting timer %s', self.trigger_time)
        logging.debug('there are %s participating rules', len(self.participating_rules))
        time_until_trigger = self.time_difference_in_seconds(
            self.trigger_time,
            datetime.now().time()
        )
        repeat_counter = 0
        while True:
            logging.debug('timer triggers in %sS', time_until_trigger)
            await asyncio.sleep(time_until_trigger)
            self.triggered = True
            if self.repeat_every == 0:
                time_until_trigger = self.time_difference_in_seconds(
                    self.trigger_time,
                    datetime.now().time()
                )
            else:
                time_until_trigger = self.repeat_every - self.duration
                if self.max_repeats != 0:
                    repeat_counter += 1
                    if repeat_counter >= self.max_repeats:
                        time_until_trigger = self.time_difference_in_seconds(
                            self.trigger_time,
                            datetime.now().time()
                        )
                        self.triggered = False
                        repeat_counter = 0
            self.activated = True
            self._apply_rules('activated', True)
            logging.debug('duration is %sS', self.duration)
            await asyncio.sleep(self.duration)
            self.activated = False
            self._apply_rules('activated', False)


