import datetime
import unittest
import uuid
from typing import Dict, List, Optional, Set, Union

from strong_typing.schema import validate_object
from strong_typing.serialization import json_to_object, object_to_json

from sample_types import *


def test_function():
    pass


async def test_async_function():
    pass


class TestSerialization(unittest.TestCase):
    def test_composite_object(self):
        json_dict = object_to_json(SimpleObjectExample())
        validate_object(SimpleObjectExample, json_dict)

        json_dict = object_to_json(AnnotatedSimpleObjectExample())
        validate_object(AnnotatedSimpleObjectExample, json_dict)

        json_dict = object_to_json(CompositeObjectExample())
        validate_object(CompositeObjectExample, json_dict)

        json_dict = object_to_json(NestedObjectExample())
        validate_object(NestedObjectExample, json_dict)

    def test_serialization_simple(self):
        self.assertEqual(object_to_json(None), None)
        self.assertEqual(object_to_json(True), True)
        self.assertEqual(object_to_json(23), 23)
        self.assertEqual(object_to_json(4.5), 4.5)
        self.assertEqual(object_to_json("an"), "an")
        self.assertEqual(object_to_json(bytes([65, 78])), "QU4=")
        self.assertEqual(object_to_json(Side.LEFT), "L")
        self.assertEqual(object_to_json(Suit.Diamonds), 1)
        self.assertEqual(
            object_to_json(datetime.datetime(1989, 10, 23, 1, 45, 50)),
            "1989-10-23T01:45:50",
        )
        self.assertEqual(
            object_to_json(
                datetime.datetime(1989, 10, 23, 1, 45, 50, tzinfo=datetime.timezone.utc)
            ),
            "1989-10-23T01:45:50+00:00",
        )
        self.assertEqual(
            object_to_json(uuid.UUID("f81d4fae-7dec-11d0-a765-00a0c91e6bf6")),
            "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
        )

    def test_serialization_collection(self):
        self.assertEqual(object_to_json([1, 2, 3]), [1, 2, 3])
        self.assertEqual(
            object_to_json({"a": 1, "b": 2, "c": 3}), {"a": 1, "b": 2, "c": 3}
        )
        self.assertEqual(object_to_json(set([1, 2, 3])), [1, 2, 3])

    def test_serialization_composite(self):
        self.assertEqual(object_to_json(UID("1.2.3.4567.8900")), "1.2.3.4567.8900")
        self.assertEqual(
            object_to_json(BinaryValueExample(bytes([65, 78]))), {"value": "QU4="}
        )

    def test_serialization_error(self):
        self.assertRaises(TypeError, object_to_json, test_function)  # function
        self.assertRaises(TypeError, object_to_json, test_async_function)  # function
        self.assertRaises(TypeError, object_to_json, TestSerialization)  # class
        self.assertRaises(
            TypeError, object_to_json, self.test_serialization_error
        )  # method

    def test_deserialization_simple(self):
        self.assertEqual(json_to_object(type(None), None), None)
        self.assertEqual(json_to_object(bool, True), True)
        self.assertEqual(json_to_object(int, 23), 23)
        self.assertEqual(json_to_object(float, 4.5), 4.5)
        self.assertEqual(json_to_object(str, "an"), "an")
        self.assertEqual(json_to_object(bytes, "QU4="), bytes([65, 78]))
        self.assertEqual(json_to_object(Side, "L"), Side.LEFT)
        self.assertEqual(json_to_object(Suit, 1), Suit.Diamonds)
        self.assertEqual(
            json_to_object(datetime.datetime, "1989-10-23T01:45:50"),
            datetime.datetime(1989, 10, 23, 1, 45, 50),
        )
        self.assertEqual(
            json_to_object(datetime.datetime, "1989-10-23T01:45:50Z"),
            datetime.datetime(1989, 10, 23, 1, 45, 50, tzinfo=datetime.timezone.utc),
        )
        timezone_cet = datetime.timezone(datetime.timedelta(seconds=3600))
        self.assertEqual(
            json_to_object(datetime.datetime, "1989-10-23T01:45:50+01:00"),
            datetime.datetime(1989, 10, 23, 1, 45, 50, tzinfo=timezone_cet),
        )
        self.assertEqual(
            json_to_object(uuid.UUID, "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"),
            uuid.UUID("f81d4fae-7dec-11d0-a765-00a0c91e6bf6"),
        )

    def test_deserialization_composite(self):
        self.assertEqual(json_to_object(UID, "1.2.3.4567.8900"), UID("1.2.3.4567.8900"))
        self.assertEqual(
            json_to_object(BinaryValueExample, {"value": "QU4="}),
            BinaryValueExample(bytes([65, 78])),
        )

    def test_deserialization_collection(self):
        self.assertEqual(json_to_object(List[int], [1, 2, 3]), [1, 2, 3])
        self.assertEqual(
            json_to_object(Dict[str, int], {"a": 1, "b": 2, "c": 3}),
            {"a": 1, "b": 2, "c": 3},
        )
        self.assertEqual(json_to_object(Set[int], [1, 2, 3]), set([1, 2, 3]))
        self.assertEqual(json_to_object(Optional[int], None), None)
        self.assertEqual(json_to_object(Optional[int], 42), 42)
        self.assertEqual(json_to_object(Union[int, str], 42), 42)
        self.assertEqual(json_to_object(Union[int, str], "a string"), "a string")
        self.assertEqual(json_to_object(Union[SimpleValueExample, int], 42), 42)
        self.assertEqual(
            json_to_object(Union[int, SimpleValueExample], {"value": 42}),
            SimpleValueExample(42),
        )
        self.assertEqual(
            json_to_object(
                Union[SimpleObjectExample, SimpleValueExample], {"value": 42}
            ),
            SimpleValueExample(42),
        )

        with self.assertRaises(TypeError):
            json_to_object(None, 23)
        with self.assertRaises(TypeError):
            json_to_object(int, "int")
        with self.assertRaises(TypeError):
            json_to_object(str, 1982)
        with self.assertRaises(KeyError):
            json_to_object(Union[int, str], 10.23)

    def test_object_serialization(self):
        """Test composition and inheritance with object serialization."""

        json_dict = object_to_json(SimpleObjectExample())
        self.assertDictEqual(
            json_dict,
            {
                "bool_value": True,
                "int_value": 23,
                "float_value": 4.5,
                "str_value": "string",
                "date_value": "1970-01-01",
                "time_value": "06:15:30",
                "datetime_value": "1989-10-23T01:45:50",
                "guid_value": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
            },
        )

        json_dict = object_to_json(
            CompositeObjectExample(
                list_value=["a", "b", "c"],
                dict_value={"key": 42},
                set_value=set(i for i in range(0, 4)),
            )
        )
        self.assertDictEqual(
            json_dict,
            {
                "list_value": ["a", "b", "c"],
                "dict_value": {"key": 42},
                "set_value": [0, 1, 2, 3],
                "tuple_value": [True, 2, "three"],
                "named_tuple_value": {"int_value": 1, "str_value": "second"},
            },
        )

        json_dict = object_to_json(InheritanceExample())
        self.assertDictEqual(
            json_dict,
            {
                "bool_value": True,
                "int_value": 23,
                "float_value": 4.5,
                "str_value": "string",
                "date_value": "1970-01-01",
                "time_value": "06:15:30",
                "datetime_value": "1989-10-23T01:45:50",
                "guid_value": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
                "list_value": [],
                "dict_value": {},
                "set_value": [],
                "tuple_value": [True, 2, "three"],
                "named_tuple_value": {"int_value": 1, "str_value": "second"},
                "extra_int_value": 0,
                "extra_str_value": "zero",
                "extra_optional_value": "value",
            },
        )

        json_dict = object_to_json(NestedObjectExample())
        self.assertDictEqual(
            json_dict,
            {
                "obj_value": {
                    "list_value": ["a", "b", "c"],
                    "dict_value": {"key": 42},
                    "set_value": [],
                    "tuple_value": [True, 2, "three"],
                    "named_tuple_value": {"int_value": 1, "str_value": "second"},
                },
                "list_value": [{"value": 1}, {"value": 2}],
                "dict_value": {
                    "a": {"value": 3},
                    "b": {"value": 4},
                    "c": {"value": 5},
                },
            },
        )

    def test_object_deserialization(self):
        """Test composition and inheritance with object de-serialization."""

        json_dict = object_to_json(NestedObjectExample())
        obj = json_to_object(NestedObjectExample, json_dict)
        self.assertEqual(obj, NestedObjectExample())


if __name__ == "__main__":
    unittest.main()
