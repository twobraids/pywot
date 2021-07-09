#!/usr/bin/env python3

import asyncio
import logging
from unittest import (
    TestCase,
    main,
)
from unittest.mock import (
    Mock,
    MagicMock,
    patch
)

import pellet_stove

from configmanners.dotdict import (
    DotDict
)


def AsyncMock(*args, **kwargs):
    """credit: https://blog.miguelgrinberg.com/post/unit-testing-asyncio-code"""
    m = MagicMock(*args, **kwargs)

    async def mock_coro(*args, **kwargs):
        the_mock = m(*args, **kwargs)
        await asyncio.sleep(10)
        return the_mock

    mock_coro.m = m
    return mock_coro


def run_async(an_event_loop, a_coroutine):
    """credit: https://blog.miguelgrinberg.com/post/unit-testing-asyncio-code"""
    return an_event_loop.run_until_complete(a_coroutine)


class MockControllerImplementation:
    def set_on_high(self):
        logging.debug('controller set to high')

    def set_on_medium(self):
        logging.debug('controller set to medium')

    def set_on_low(self):
        logging.debug('controller set to low')

    def set_off(self):
        logging.debug('controller set to off')

    def shutdown(self):
        logging.debug('controller shutdown')


class PelletStoveTest(TestCase):
    def setUp(self):
        # setup async loop
        self.eventloop = asyncio.get_event_loop()

    def tearDown(self):
        # clear and close async loop
        pass

    def _new_config(self):
        c = DotDict({
            "startup_level": "high",
            "medium_linger_time_in_minutes": 0,
            "medium_linger_time_in_seconds": 0,
            "low_linger_time_in_minutes": 0,
            "low_linger_time_in_seconds": 0,
            "controller_implementation_class": MockControllerImplementation
        })
        return c

    def test_instantiation(self):
        config = self._new_config()
        ps = pellet_stove.PelletStove(config)
        self.assertFalse(ps.thermostat_state)
        self.assertEqual(ps.stove_state, "off")
        self.assertEqual(ps.stove_automation_mode, "off")

    @patch('test_pellet_stove.MockControllerImplementation.set_on_high')
    def test_set_stove_mode_to_heating_with_no_lingering_shutdown_task(self, set_on_high_mock):
        config = self._new_config()
        ps = pellet_stove.PelletStove(config)
        run_async(self.eventloop, ps.set_stove_mode_to_heating())

        self.assertEqual('high', ps.stove_state)
        self.assertEqual('heating', ps.stove_automation_mode)

    def test_set_stove_mode_to_heating_with_lingering_shutdown_task(self):
        config = self._new_config()
        ps = pellet_stove.PelletStove(config)
        coro = AsyncMock()
        ps.lingering_shutdown_task = asyncio.ensure_future(coro())
        run_async(self.eventloop, ps.set_stove_mode_to_heating())

        self.assertEqual('high', ps.stove_state)
        self.assertEqual('heating', ps.stove_automation_mode)
        coro.m.assert_called_once_with()
        self.assertFalse(ps.lingering_shutdown_task)

    def test_set_stove_mode_to_lingering(self):
        config = self._new_config()
        ps = pellet_stove.PelletStove(config)
        ps._controller = Mock()
        run_async(self.eventloop, ps.set_stove_mode_to_lingering())

        ps._controller.set_on_medium.assert_called_once_with()
        ps._controller.set_on_low.assert_called_once_with()
        ps._controller.set_off.assert_called_once_with()

    def test_shutdown_with_no_lingering_shutdown_task(self):
        config = self._new_config()
        ps = pellet_stove.PelletStove(config)
        ps._controller = Mock()
        ps.shutdown()

        ps._controller.shutdown.assert_called_once_with()

    def test_run_scenario_1(self):
        config = self._new_config()
        ps = pellet_stove.PelletStove(config)
        ps._controller = Mock()
        ps._controller.get_thermostat_state.side_effect = [False, True, False, False]

        async def scenario_1():
            await ps.get_thermostat_state()

            self.assertFalse(ps.thermostat_state)
            self.assertEqual(ps.stove_state, 'off')
            self.assertEqual(ps.stove_automation_mode, 'off')

            await ps.get_thermostat_state()

            self.assertTrue(ps.thermostat_state)
            self.assertEqual(ps.stove_state, 'high')
            self.assertEqual(ps.stove_automation_mode, 'heating')
            ps._controller.set_on_high.called_once_with()

            await ps.get_thermostat_state()
            await ps.lingering_shutdown_task

            self.assertFalse(ps.thermostat_state)
            self.assertTrue(ps.lingering_shutdown_task is None)
            self.assertEqual(ps.stove_state, 'off')
            self.assertEqual(ps.stove_automation_mode, 'off')
            ps._controller.set_on_medium.called_once_with()
            ps._controller.set_on_low.called_once_with()
            ps._controller.set_off.called_once_with()

        run_async(self.eventloop, scenario_1())

    def test_run_scenario_2(self):
        config = self._new_config()
        ps = pellet_stove.PelletStove(config)
        ps._controller = Mock()
        ps._controller.get_thermostat_state.side_effect = [False, True, False, True]

        async def scenario_2():
            await ps.get_thermostat_state()

            self.assertFalse(ps.thermostat_state)
            self.assertEqual(ps.stove_state, 'off')
            self.assertEqual(ps.stove_automation_mode, 'off')

            await ps.get_thermostat_state()

            self.assertTrue(ps.thermostat_state)
            self.assertEqual(ps.stove_state, 'high')
            self.assertEqual(ps.stove_automation_mode, 'heating')
            ps._controller.set_on_high.called_once_with()

            await ps.get_thermostat_state()
            await ps.get_thermostat_state()

            self.assertTrue(ps.thermostat_state)
            self.assertTrue(ps.lingering_shutdown_task is None)
            self.assertEqual(ps.stove_state, 'high')
            self.assertEqual(ps.stove_automation_mode, 'heating')
            ps._controller.set_on_medium.called_once_with()
            ps._controller.set_on_low.called_once_with()
            ps._controller.set_off.called_once_with()

        run_async(self.eventloop, scenario_2())


if __name__ == '__main__':
    main()
