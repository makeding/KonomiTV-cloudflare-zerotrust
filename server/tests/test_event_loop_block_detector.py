import asyncio
import unittest
from unittest.mock import patch

from app.utils.EventLoopBlockDetector import MonitorEventLoopBlocking


class EventLoopBlockDetectorTest(unittest.IsolatedAsyncioTestCase):
    async def test_monitor_arms_faulthandler_and_cancels_timer_on_shutdown(self) -> None:
        """イベントループ監視が faulthandler を起動し、終了時にタイマーを残さない。"""

        with (
            patch('app.utils.EventLoopBlockDetector.EVENT_LOOP_HEARTBEAT_INTERVAL_SECONDS', 60.0),
            patch('app.utils.EventLoopBlockDetector.GetServerLogStream'),
            patch('app.utils.EventLoopBlockDetector.faulthandler.dump_traceback_later') as dump_traceback_later,
            patch('app.utils.EventLoopBlockDetector.faulthandler.cancel_dump_traceback_later') as cancel_dump,
        ):
            monitor_task = asyncio.create_task(MonitorEventLoopBlocking())
            await asyncio.sleep(0)
            monitor_task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await monitor_task

        dump_traceback_later.assert_called_once()
        self.assertGreaterEqual(cancel_dump.call_count, 2)
