import datetime
import random
import string
import unittest
import uuid
from dataclasses import dataclass

from test_timer import Timer

from strong_typing.serialization import json_to_object, object_to_json


def time_today(time_of_day: datetime.time) -> datetime.datetime:
    return datetime.datetime.combine(
        datetime.datetime.today(), time_of_day, time_of_day.tzinfo
    )


def random_datetime(
    start: datetime.datetime, end: datetime.datetime
) -> datetime.datetime:
    """
    Returns a random datetime between two datetime objects.
    """

    delta = end - start
    seconds = delta.days * 86400 + delta.seconds
    return start + datetime.timedelta(seconds=random.randrange(seconds))


def random_date(start: datetime.date, end: datetime.date) -> datetime.date:
    """
    Returns a random date between two date objects.
    """

    delta = end - start
    days = delta.days
    return start + datetime.timedelta(days=random.randrange(days))


def random_time(start: datetime.time, end: datetime.time) -> datetime.time:
    """
    Returns a random time between two time objects.
    """

    ts_end = time_today(end)
    ts_start = time_today(start)
    delta = ts_end - ts_start
    seconds = delta.days * 86400 + delta.seconds
    ts = ts_start + datetime.timedelta(seconds=random.randrange(seconds))
    return ts.timetz()


@dataclass
class SimpleObjectExample:
    "A simple data class with multiple properties."

    bool_value: bool
    int_value: int
    float_value: float
    str_value: str
    date_value: datetime.date
    time_value: datetime.time
    datetime_value: datetime.datetime
    guid_value: uuid.UUID


def create_randomized_object() -> SimpleObjectExample:
    return SimpleObjectExample(
        bool_value=random.uniform(0.0, 1.0) > 0.5,
        int_value=random.randint(0, 1024),
        float_value=random.uniform(0.0, 1.0),
        str_value="".join(random.choices(string.ascii_letters + string.digits, k=64)),
        date_value=random_date(datetime.date(1982, 10, 23), datetime.date(2022, 9, 25)),
        time_value=random_time(
            datetime.time(2, 30, 0, tzinfo=datetime.timezone.utc),
            datetime.time(18, 45, 0, tzinfo=datetime.timezone.utc),
        ),
        datetime_value=random_datetime(
            datetime.datetime(1982, 10, 23, 2, 30, 0, tzinfo=datetime.timezone.utc),
            datetime.datetime(2022, 9, 25, 18, 45, 0, tzinfo=datetime.timezone.utc),
        ),
        guid_value=uuid.uuid4(),
    )


class TestPerformance(unittest.TestCase):
    def test_serialization(self) -> None:
        original_items = [create_randomized_object() for k in range(100000)]

        with Timer("serialization"):
            serialized_items = [object_to_json(item) for item in original_items]

        with Timer("deserialization"):
            deserialized_items = [
                json_to_object(SimpleObjectExample, item) for item in serialized_items
            ]

        self.assertListEqual(original_items, deserialized_items)


if __name__ == "__main__":
    unittest.main()
