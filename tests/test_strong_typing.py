"""Unit tests for strong typing."""

import datetime
import enum
import unittest
from dataclasses import dataclass, field
from typing import Dict, List

from strong_typing import (
    JsonSchemaGenerator,
    json_schema_type,
    json_to_object,
    object_to_json,
    validate_object,
)


class Side(enum.Enum):
    LEFT = "L"
    RIGHT = "R"


class Suit(enum.Enum):
    Diamonds = 1
    Hearts = 2
    Clubs = 3
    Spades = 4


@dataclass
class SimpleValueExample:
    value: int = 23


@dataclass
class BinaryValueExample:
    value: bytes


@dataclass
class SimpleObjectExample:
    bool_value: bool = True
    int_value: int = 23
    float_value: float = 4.5
    str_value: str = "string"
    datetime_value: datetime.datetime = datetime.datetime(1989, 10, 23, 1, 45, 50)


@dataclass
class ObjectExample(SimpleObjectExample):
    list_value: List[str] = field(default_factory=list)
    dict_value: Dict[str, int] = field(default_factory=dict)


@dataclass
@json_schema_type
class ValueExample:
    value: int = 0


@dataclass
class CompositeExample:
    obj_value: ObjectExample
    list_value: List[ValueExample]
    dict_value: Dict[str, ValueExample]

    def __init__(self):
        self.obj_value = ObjectExample(
            list_value=["a", "b", "c"], dict_value={"key": 42}
        )
        self.list_value = [ValueExample(value=1), ValueExample(value=2)]
        self.dict_value = {
            "a": ValueExample(value=3),
            "b": ValueExample(value=4),
            "c": ValueExample(value=5),
        }


def test_function():
    pass


async def test_async_function():
    pass


class TestStrongTyping(unittest.TestCase):
    def test_composite_object(self):
        json_dict = object_to_json(CompositeExample())
        validate_object(CompositeExample, json_dict)

    def test_schema(self):
        generator = JsonSchemaGenerator(use_descriptions=False)
        self.assertEqual(generator.type_to_schema(bool), {"type": "boolean"})
        self.assertEqual(generator.type_to_schema(int), {"type": "integer"})
        self.assertEqual(generator.type_to_schema(float), {"type": "number"})
        self.assertEqual(generator.type_to_schema(str), {"type": "string"})
        self.assertEqual(
            generator.type_to_schema(bytes),
            {"type": "string", "contentEncoding": "base64"},
        )
        self.assertEqual(
            generator.type_to_schema(Side), {"enum": ["L", "R"], "type": "string"}
        )
        self.assertEqual(
            generator.type_to_schema(Suit), {"enum": [1, 2, 3, 4], "type": "integer"}
        )
        self.assertEqual(
            generator.type_to_schema(List[int]),
            {"type": "array", "items": {"type": "integer"}},
        )
        self.assertEqual(
            generator.type_to_schema(Dict[str, int]),
            {"type": "object", "additionalProperties": {"type": "integer"}},
        )
        self.assertEqual(
            generator.type_to_schema(SimpleValueExample),
            {
                "type": "object",
                "properties": {"value": {"type": "integer", "default": 23}},
                "additionalProperties": False,
                "required": ["value"],
            },
        )
        self.assertEqual(
            generator.type_to_schema(ValueExample),
            {"$ref": "#/definitions/ValueExample"},
        )

    def test_serialization(self):
        self.assertEqual(object_to_json(True), True)
        self.assertEqual(object_to_json(23), 23)
        self.assertEqual(object_to_json(4.5), 4.5)
        self.assertEqual(object_to_json("an"), "an")
        self.assertEqual(object_to_json(bytes([65, 78])), "QU4=")
        self.assertEqual(object_to_json(Side.LEFT), "L")
        self.assertEqual(object_to_json(Suit.Diamonds), 1)
        self.assertEqual(
            object_to_json(BinaryValueExample(bytes([65, 78]))), {"value": "QU4="}
        )

        self.assertRaises(TypeError, object_to_json, test_function)  # function
        self.assertRaises(TypeError, object_to_json, test_async_function)  # function
        self.assertRaises(TypeError, object_to_json, TestStrongTyping)  # class
        self.assertRaises(TypeError, object_to_json, self.test_serialization)  # method

    def test_deserialization(self):
        self.assertEqual(json_to_object(bool, True), True)
        self.assertEqual(json_to_object(int, 23), 23)
        self.assertEqual(json_to_object(float, 4.5), 4.5)
        self.assertEqual(json_to_object(str, "an"), "an")
        self.assertEqual(json_to_object(bytes, "QU4="), bytes([65, 78]))
        self.assertEqual(json_to_object(Side, "L"), Side.LEFT)
        self.assertEqual(json_to_object(Suit, 1), Suit.Diamonds)
        self.assertEqual(
            json_to_object(BinaryValueExample, {"value": "QU4="}),
            BinaryValueExample(bytes([65, 78])),
        )

    def test_object_serialization(self):
        """Test composition and inheritance with object serialization."""

        json_dict = object_to_json(CompositeExample())
        self.assertDictEqual(
            json_dict,
            {
                "obj_value": {
                    "bool_value": True,
                    "int_value": 23,
                    "float_value": 4.5,
                    "str_value": "string",
                    "list_value": ["a", "b", "c"],
                    "dict_value": {"key": 42},
                    "datetime_value": "1989-10-23T01:45:50",
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

        json_dict = object_to_json(CompositeExample())
        obj = json_to_object(CompositeExample, json_dict)
        self.assertEqual(obj, CompositeExample())


if __name__ == "__main__":
    unittest.main()