"""Unit tests for strong typing."""

from __future__ import annotations

import datetime
import decimal
import enum
import unittest
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, NamedTuple, Optional, Set, Tuple, Union

from strong_typing.auxiliary import Annotated, IntegerRange, MaxLength, Precision
from strong_typing.schema import (
    JsonSchemaGenerator,
    SchemaOptions,
    Validator,
    classdef_to_schema,
    get_class_docstrings,
    json_schema_type,
    validate_object,
    JsonType,
)
from strong_typing.serialization import json_to_object, object_to_json


class Side(enum.Enum):
    "An enumeration with string values."

    LEFT = "L"
    RIGHT = "R"


class Suit(enum.Enum):
    "An enumeration with numeric values."

    Diamonds = 1
    Hearts = 2
    Clubs = 3
    Spades = 4


@dataclass
class SimpleValueExample:
    "A simple data class with a single property."

    value: int = 23


@dataclass
class BinaryValueExample:
    value: bytes


@json_schema_type(
    schema={
        "type": "string",
        "pattern": r"^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*$",
        "maxLength": 64,
    }
)
@dataclass
class UID:
    """A unique identifier in DICOM."""

    value: str

    def to_json(self) -> str:
        return self.value

    @classmethod
    def from_json(cls, value: str) -> UID:
        return UID(value)


class SimpleNamedTuple(NamedTuple):
    "A simple named tuple."

    int_value: int
    str_value: str


@dataclass
class SimpleObjectExample:
    "A simple data class with multiple properties."

    bool_value: bool = True
    int_value: int = 23
    float_value: float = 4.5
    str_value: str = "string"
    date_value: datetime.date = datetime.date(1970, 1, 1)
    time_value: datetime.time = datetime.time(6, 15, 30)
    datetime_value: datetime.datetime = datetime.datetime(1989, 10, 23, 1, 45, 50)
    guid_value: uuid.UUID = uuid.UUID("f81d4fae-7dec-11d0-a765-00a0c91e6bf6")


@dataclass
class AnnotatedSimpleObjectExample:
    "A simple data class with multiple properties."

    int_value: Annotated[int, IntegerRange(19, 82)] = 23
    float_value: Annotated[
        float, Precision(significant_digits=6, decimal_digits=3)
    ] = 4.5
    str_value: Annotated[str, MaxLength(64)] = "string"


@dataclass
class CompositeObjectExample:
    list_value: List[str] = field(default_factory=list)
    dict_value: Dict[str, int] = field(default_factory=dict)
    set_value: Set[int] = field(default_factory=set)
    tuple_value: Tuple[bool, int, str] = (True, 2, "three")
    named_tuple_value: SimpleNamedTuple = SimpleNamedTuple(1, "second")
    optional_value: Optional[str] = None


@dataclass
class InheritanceExample(SimpleObjectExample, CompositeObjectExample):
    extra_int_value: int = 0
    extra_str_value: str = "zero"
    extra_optional_value: Optional[str] = "value"


@dataclass
@json_schema_type
class ValueExample:
    "A value of a fundamental type wrapped into an object."

    value: int = 0


@dataclass
class NestedObjectExample:
    obj_value: CompositeObjectExample
    list_value: List[ValueExample]
    dict_value: Dict[str, ValueExample]

    def __init__(self):
        self.obj_value = CompositeObjectExample(
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
        json_dict = object_to_json(SimpleObjectExample())
        validate_object(SimpleObjectExample, json_dict)

        json_dict = object_to_json(AnnotatedSimpleObjectExample())
        validate_object(AnnotatedSimpleObjectExample, json_dict)

        json_dict = object_to_json(CompositeObjectExample())
        validate_object(CompositeObjectExample, json_dict)

        json_dict = object_to_json(NestedObjectExample())
        validate_object(NestedObjectExample, json_dict)

    def test_schema(self):
        options = SchemaOptions(use_descriptions=True)
        generator = JsonSchemaGenerator(options)
        self.assertEqual(generator.type_to_schema(type(None)), {"type": "null"})
        self.assertEqual(generator.type_to_schema(bool), {"type": "boolean"})
        self.assertEqual(generator.type_to_schema(int), {"type": "integer"})
        self.assertEqual(generator.type_to_schema(float), {"type": "number"})
        self.assertEqual(generator.type_to_schema(str), {"type": "string"})
        self.assertEqual(
            generator.type_to_schema(bytes),
            {"type": "string", "contentEncoding": "base64"},
        )
        self.assertEqual(
            generator.type_to_schema(Side),
            {
                "enum": ["L", "R"],
                "type": "string",
                "title": "An enumeration with string values.",
            },
        )
        self.assertEqual(
            generator.type_to_schema(Suit),
            {
                "enum": [1, 2, 3, 4],
                "type": "integer",
                "title": "An enumeration with numeric values.",
            },
        )
        self.assertEqual(
            generator.type_to_schema(Any),
            {
                "oneOf": [
                    {"type": "null"},
                    {"type": "boolean"},
                    {"type": "number"},
                    {"type": "string"},
                    {"type": "array"},
                    {"type": "object"},
                ]
            },
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
            generator.type_to_schema(Set[int]),
            {"type": "array", "items": {"type": "integer"}, "uniqueItems": True},
        )
        self.assertEqual(
            generator.type_to_schema(Union[int, str]),
            {"oneOf": [{"type": "integer"}, {"type": "string"}]},
        )
        self.assertEqual(
            generator.type_to_schema(Tuple[bool, int, str]),
            {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "prefixItems": [
                    {"type": "boolean"},
                    {"type": "integer"},
                    {"type": "string"},
                ],
            },
        )
        self.assertEqual(
            generator.type_to_schema(SimpleValueExample),
            {
                "type": "object",
                "properties": {"value": {"type": "integer", "default": 23}},
                "additionalProperties": False,
                "required": ["value"],
                "title": "A simple data class with a single property.",
            },
        )
        self.assertEqual(
            generator.type_to_schema(SimpleNamedTuple),
            {
                "type": "object",
                "properties": {
                    "int_value": {"type": "integer"},
                    "str_value": {"type": "string"},
                },
                "additionalProperties": False,
                "required": ["int_value", "str_value"],
                "title": "A simple named tuple.",
            },
        )
        self.assertEqual(
            generator.type_to_schema(ValueExample),
            {"$ref": "#/definitions/ValueExample"},
        )
        self.assertEqual(
            classdef_to_schema(UID, options, validator=Validator.Draft7),
            {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "definitions": {
                    "UID": {
                        "type": "string",
                        "pattern": "^(0|[1-9][0-9]*)(\\.(0|[1-9][0-9]*))*$",
                        "maxLength": 64,
                        "title": "A unique identifier in DICOM.",
                    }
                },
                "$ref": "#/definitions/UID",
            },
        )
        self.assertEqual(
            classdef_to_schema(UID, options),
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "definitions": {
                    "UID": {
                        "type": "string",
                        "pattern": "^(0|[1-9][0-9]*)(\\.(0|[1-9][0-9]*))*$",
                        "maxLength": 64,
                        "title": "A unique identifier in DICOM.",
                    }
                },
                "$ref": "#/definitions/UID",
            },
        )

    def test_registered_schema(self):
        self.maxDiff = None
        self.assertEqual(
            classdef_to_schema(JsonType),
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "definitions": {
                    "JsonType": {
                        "oneOf": [
                            {"type": "null"},
                            {"type": "boolean"},
                            {"type": "integer"},
                            {"type": "number"},
                            {"type": "string"},
                            {
                                "type": "object",
                                "additionalProperties": {
                                    "$ref": "#/definitions/JsonType"
                                },
                            },
                            {
                                "type": "array",
                                "items": {"$ref": "#/definitions/JsonType"},
                            },
                        ],
                        "examples": [
                            {
                                "property1": None,
                                "property2": True,
                                "property3": 64,
                                "property4": "string",
                                "property5": ["item"],
                                "property6": {"key": "value"},
                            }
                        ],
                    }
                },
                "$ref": "#/definitions/JsonType",
            },
        )

    def test_schema_annotated(self):
        options = SchemaOptions(use_descriptions=False)
        generator = JsonSchemaGenerator(options)
        self.assertEqual(
            generator.type_to_schema(Annotated[int, IntegerRange(23, 82)]),
            {
                "type": "integer",
                "minimum": 23,
                "maximum": 82,
            },
        )
        self.assertEqual(
            generator.type_to_schema(Annotated[float, Precision(9, 6)]),
            {
                "type": "number",
                "multipleOf": 0.000001,
                "exclusiveMinimum": -1000,
                "exclusiveMaximum": 1000,
            },
        )
        self.assertEqual(
            generator.type_to_schema(Annotated[decimal.Decimal, Precision(9, 6)]),
            {
                "type": "number",
                "multipleOf": 0.000001,
                "exclusiveMinimum": -1000,
                "exclusiveMaximum": 1000,
            },
        )
        self.assertEqual(
            generator.type_to_schema(AnnotatedSimpleObjectExample),
            {
                "type": "object",
                "properties": {
                    "int_value": {
                        "type": "integer",
                        "default": 23,
                        "minimum": 19,
                        "maximum": 82,
                    },
                    "float_value": {
                        "type": "number",
                        "default": 4.5,
                        "multipleOf": 0.001,
                        "exclusiveMinimum": -1000,
                        "exclusiveMaximum": 1000,
                    },
                    "str_value": {
                        "type": "string",
                        "default": "string",
                        "maxLength": 64,
                    },
                },
                "additionalProperties": False,
                "required": ["int_value", "float_value", "str_value"],
            },
        )

    def _assert_docstring_equal(self, generator: JsonSchemaGenerator, typ: type):
        "Checks if the Python class docstring matches the title and description strings in the generated JSON schema."

        short_description, long_description = get_class_docstrings(typ)
        self.assertEqual(
            generator.type_to_schema(typ).get("title"),
            short_description,
        )
        self.assertEqual(
            generator.type_to_schema(typ).get("description"),
            long_description,
        )

    def test_docstring(self):
        self.maxDiff = None
        options = SchemaOptions(use_descriptions=True)
        generator = JsonSchemaGenerator(options)

        # never extract docstring simple types
        self.assertEqual(generator.type_to_schema(type(None)), {"type": "null"})
        self.assertEqual(generator.type_to_schema(bool), {"type": "boolean"})
        self.assertEqual(generator.type_to_schema(int), {"type": "integer"})
        self.assertEqual(generator.type_to_schema(float), {"type": "number"})
        self.assertEqual(generator.type_to_schema(str), {"type": "string"})
        self.assertEqual(
            generator.type_to_schema(datetime.date),
            {"type": "string", "format": "date"},
        )
        self.assertEqual(
            generator.type_to_schema(datetime.time),
            {"type": "string", "format": "time"},
        )
        self.assertEqual(
            generator.type_to_schema(uuid.UUID), {"type": "string", "format": "uuid"}
        )

        # parse docstring for complex types
        self._assert_docstring_equal(generator, Suit)
        self._assert_docstring_equal(generator, SimpleObjectExample)

    def test_serialization(self):
        self.assertEqual(object_to_json(None), None)
        self.assertEqual(object_to_json(True), True)
        self.assertEqual(object_to_json(23), 23)
        self.assertEqual(object_to_json(4.5), 4.5)
        self.assertEqual(object_to_json("an"), "an")
        self.assertEqual(object_to_json(bytes([65, 78])), "QU4=")
        self.assertEqual(object_to_json(Side.LEFT), "L")
        self.assertEqual(object_to_json(Suit.Diamonds), 1)
        self.assertEqual(object_to_json(UID("1.2.3.4567.8900")), "1.2.3.4567.8900")
        self.assertEqual(
            object_to_json(BinaryValueExample(bytes([65, 78]))), {"value": "QU4="}
        )
        self.assertEqual(
            object_to_json(uuid.UUID("f81d4fae-7dec-11d0-a765-00a0c91e6bf6")),
            "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
        )

        self.assertEqual(object_to_json([1, 2, 3]), [1, 2, 3])
        self.assertEqual(
            object_to_json({"a": 1, "b": 2, "c": 3}), {"a": 1, "b": 2, "c": 3}
        )
        self.assertEqual(object_to_json(set([1, 2, 3])), [1, 2, 3])

        self.assertRaises(TypeError, object_to_json, test_function)  # function
        self.assertRaises(TypeError, object_to_json, test_async_function)  # function
        self.assertRaises(TypeError, object_to_json, TestStrongTyping)  # class
        self.assertRaises(TypeError, object_to_json, self.test_serialization)  # method

    def test_deserialization(self):
        self.assertEqual(json_to_object(type(None), None), None)
        self.assertEqual(json_to_object(bool, True), True)
        self.assertEqual(json_to_object(int, 23), 23)
        self.assertEqual(json_to_object(float, 4.5), 4.5)
        self.assertEqual(json_to_object(str, "an"), "an")
        self.assertEqual(json_to_object(bytes, "QU4="), bytes([65, 78]))
        self.assertEqual(json_to_object(Side, "L"), Side.LEFT)
        self.assertEqual(json_to_object(Suit, 1), Suit.Diamonds)
        self.assertEqual(json_to_object(UID, "1.2.3.4567.8900"), UID("1.2.3.4567.8900"))
        self.assertEqual(
            json_to_object(BinaryValueExample, {"value": "QU4="}),
            BinaryValueExample(bytes([65, 78])),
        )
        self.assertEqual(
            json_to_object(uuid.UUID, "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"),
            uuid.UUID("f81d4fae-7dec-11d0-a765-00a0c91e6bf6"),
        )

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
