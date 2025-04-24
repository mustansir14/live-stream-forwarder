import json
from datetime import datetime, timedelta, timezone
from typing import List

from openai import OpenAI

from internal.schemas import TRWUpcomingStream, TRWCampus


class MessageParser:

    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key)

    def parse(self, message: str, campus: TRWCampus) -> List[TRWUpcomingStream]:
        prompt = """Your task is to extract information about an upcoming live stream from the provided message. The task involves identifying upcoming live streams and extracting their starting time information.

### Steps:
1. **Determine if the message mentions a live stream**:
   - Look for phrases such as "live stream," "starting in," or other temporal cues.

2. **Extract the following details if a live stream is mentioned**:
   - The name of the stream.
   - One of the following:
    - The start time of the stream in **ISO format**.
    - A relative offset from the current time (e.g., "in 5 minutes") in seconds.

### Output Format:
If a live stream is mentioned, return a JSON object structured like this:
```json
{
    "streams": [
        {
            "name": "Stream Name",
            "start_time_absolute": "YYYY-MM-DDTHH:MM:00Z",
            or
            "start_time_relative": "300"
        }
    ]
}```

Make sure only one of "start_time_absolute" or "start_time_relative" is included for each stream.

If no live stream is mentioned, return an empty array.

For your reference, today's date is %s

Message: 
\"\"\"%s\"\"\"
""" % (
            datetime.now().strftime("%d %B %Y"),
            message,
        )
        response = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            temperature=0.00000000001,
        )
        content = response.choices[0].message.content
        try:
            json_content = json.loads(content)
        except json.JSONDecodeError:
            return []

        upcoming_streams = []
        for stream in json_content["streams"]:
            start_time = datetime.now(timezone.utc)
            if "start_time_absolute" in stream:
                start_time = datetime.fromisoformat(stream["start_time_absolute"])
            elif "start_time_relative" in stream:
                start_time += timedelta(seconds=int(stream["start_time_relative"]))
            upcoming_stream = TRWUpcomingStream(
                name=stream["name"],
                start_time=round_to_nearest_15_minutes(start_time),
                campus=campus,
            )
            upcoming_streams.append(upcoming_stream)
        return upcoming_streams


def round_to_nearest_15_minutes(dt: datetime) -> datetime:
    minute = round(dt.minute / 15) * 15
    if minute == 60:
        dt += timedelta(hours=1)
        minute = 0
    return datetime(
        dt.year,
        dt.month,
        dt.day,
        dt.hour,
        minute,
        tzinfo=timezone.utc,
    )


def current_timezone():
    local_offset = datetime.now().astimezone().utcoffset()
    hours, remainder = divmod(local_offset.total_seconds(), 3600)
    minutes = remainder // 60
    gmt_timezone = (
        f"GMT{'+' if hours >= 0 else '-'}{abs(int(hours))}:{int(minutes):02d}"
    )
    return gmt_timezone, hours
