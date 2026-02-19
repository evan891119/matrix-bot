import unittest

from app.reminders.time_utils import parse_local_to_utc_iso


class TimeUtilsTest(unittest.TestCase):
    def test_asia_taipei_to_utc(self) -> None:
        utc_iso = parse_local_to_utc_iso("2026-02-20 09:00", "Asia/Taipei")
        self.assertEqual(utc_iso, "2026-02-20T01:00:00+00:00")
