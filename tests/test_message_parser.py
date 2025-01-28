import unittest
from datetime import datetime, timedelta, timezone

from internal.enums import StreamSource
from internal.env import Env
from internal.message_parser import MessageParser, round_to_nearest_15_minutes
from internal.schemas import UpcomingStream


class TestMessageParser(unittest.TestCase):
    def test_parse_message(self):

        cases = [
            {
                "message": """  LIVE STREAM IN 5 MINUTES 
⠀
Crypto Investing Analysis 20th January 2025
⠀

(If you miss this stream, it will be reposted in #｜Daily Investing Analysis for 24 hours)
⠀
No external link - Watch the stream here in TRW app.""",
                "source": StreamSource.TRW,
                "expected_output": [
                    UpcomingStream(
                        name="Crypto Investing Analysis",
                        start_time=round_to_nearest_15_minutes(
                            datetime.now(timezone.utc) + timedelta(minutes=5)
                        ),
                        source=StreamSource.TRW,
                    )
                ],
            },
            {
                "message": "Taking any questions now discussed in the stream.",
                "source": StreamSource.TRW,
                "expected_output": [],
            },
            {
                "message": """LEAD YOURSELF - PT2
Welcome to Day 2 of Winner's New Year
I know some of you have already fallen behind, haven't taken action on what you learned yesterday, and are set to fail even harder than you were last year
But thankfully that's only a few of you
The rest of you that took action on yesterday's POWER UP CALL are destined for great things in 2025
And on today's POWER UP CALL I'll show you how to take that compelling vision and convert it into reality.
▲ Warning - This process is pretty addicting once you see how fast you can change▲
This is the second half of the missing personal leadership you didn't have in 2024
Come ready to WORK
When: Today 11:00 am EST, 4:00 pm UTC""",
                "source": StreamSource.TRW,
                "expected_output": [
                    UpcomingStream(
                        name="POWER UP CALL",
                        start_time=datetime.now(timezone.utc).replace(
                            hour=16, minute=0, second=0, microsecond=0
                        ),
                        source=StreamSource.TRW,
                    )
                ],
            },
            {
                "message": """DAILY PRODUCT ANALYSIS LIVE PREMIERE - Hey @Students. Join me in 30 minutes for the first episode of the new Daily Product Analysis series.

There will be a watch-party hosted in the #live-streams channel. Don't miss it!""",
                "source": StreamSource.TRW,
                "expected_output": [
                    UpcomingStream(
                        name="Daily Product Analysis",
                        start_time=round_to_nearest_15_minutes(
                            datetime.now(timezone.utc) + timedelta(minutes=30)
                        ),
                        source=StreamSource.TRW,
                    )
                ],
            },
            {
                "message": """Last nights 4pm stream was great. Thank you guys for joining.""",
                "source": StreamSource.TRW,
                "expected_output": [],
            },
            {
                "message": """Last nights 4pm stream was great. Thank you guys for joining. The next Live Trading streams will be tomorrow at noon and then at evening at 5.""",
                "source": StreamSource.TRW,
                "expected_output": [
                    UpcomingStream(
                        name="Live Trading",
                        start_time=(
                            datetime.now(timezone.utc) + timedelta(days=1)
                        ).replace(hour=12, minute=0, second=0, microsecond=0),
                        source=StreamSource.TRW,
                    ),
                    UpcomingStream(
                        name="Live Trading",
                        start_time=(
                            datetime.now(timezone.utc) + timedelta(days=1)
                        ).replace(hour=17, minute=0, second=0, microsecond=0),
                        source=StreamSource.TRW,
                    ),
                ],
            },
        ]

        message_parser = MessageParser(openai_api_key=Env.OPENAI_API_KEY)
        for case in cases:
            self.assertEqual(
                message_parser.parse(case["message"], case["source"]),
                case["expected_output"],
            )

    def test_round_to_nearest_15_minute(self):
        cases = [
            {
                "dt": datetime(2025, 1, 1, 0, 0, 0, 0, timezone.utc),
                "expected_output": datetime(2025, 1, 1, 0, 0, 0, 0, timezone.utc),
            },
            {
                "dt": datetime(2025, 1, 1, 0, 1, 0, 0, timezone.utc),
                "expected_output": datetime(2025, 1, 1, 0, 0, 0, 0, timezone.utc),
            },
            {
                "dt": datetime(2025, 1, 1, 0, 7, 0, 0, timezone.utc),
                "expected_output": datetime(2025, 1, 1, 0, 0, 0, 0, timezone.utc),
            },
            {
                "dt": datetime(2025, 1, 1, 0, 8, 0, 0, timezone.utc),
                "expected_output": datetime(2025, 1, 1, 0, 15, 0, 0, timezone.utc),
            },
            {
                "dt": datetime(2025, 1, 1, 0, 22, 0, 0, timezone.utc),
                "expected_output": datetime(2025, 1, 1, 0, 15, 0, 0, timezone.utc),
            },
            {
                "dt": datetime(2025, 1, 1, 0, 23, 0, 0, timezone.utc),
                "expected_output": datetime(2025, 1, 1, 0, 30, 0, 0, timezone.utc),
            },
            {
                "dt": datetime(2025, 1, 1, 0, 37, 0, 0, timezone.utc),
                "expected_output": datetime(2025, 1, 1, 0, 30, 0, 0, timezone.utc),
            },
            {
                "dt": datetime(2025, 1, 1, 0, 38, 0, 0, timezone.utc),
                "expected_output": datetime(2025, 1, 1, 0, 45, 0, 0, timezone.utc),
            },
            {
                "dt": datetime(2025, 1, 1, 0, 54, 0, 0, timezone.utc),
                "expected_output": datetime(2025, 1, 1, 1, 0, 0, 0, timezone.utc),
            },
        ]

        for case in cases:
            self.assertEqual(
                round_to_nearest_15_minutes(case["dt"]),
                case["expected_output"],
            )
