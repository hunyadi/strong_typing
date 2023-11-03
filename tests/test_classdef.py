import datetime
import ipaddress
import typing
import unittest
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, List, Literal, Optional, Union

from strong_typing.auxiliary import MaxLength, Precision, float64, int16, int32, int64
from strong_typing.classdef import JsonSchemaAny, node_to_type, schema_to_type
from strong_typing.core import JsonType, Schema
from strong_typing.inspection import (
    TypeLike,
    dataclass_fields,
    is_dataclass_type,
    is_type_enum,
)
from strong_typing.schema import classdef_to_schema
from strong_typing.serialization import json_to_object

from . import empty


def as_type(schema: Schema) -> TypeLike:
    node = typing.cast(
        JsonSchemaAny, json_to_object(JsonSchemaAny, schema, context=empty)
    )
    return node_to_type(empty, "", node)


@dataclass
class UnionOfValues:
    value: Union[None, str, int]


@dataclass
class UnionOfAddresses:
    address: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]


@dataclass
class Person__residence:
    city: str
    country: Optional[str]


@dataclass
class Person:
    id: uuid.UUID
    name: str
    date_of_birth: datetime.datetime
    residence: Person__residence


class TestClassDef(unittest.TestCase):
    def assertTypeEquivalent(self, left: TypeLike, right: TypeLike) -> None:
        if is_dataclass_type(left) and is_dataclass_type(right):
            self.assertEqual(left.__name__, right.__name__)
            for left_field, right_field in zip(
                dataclass_fields(left), dataclass_fields(right)
            ):
                self.assertEqual(left_field.name, right_field.name)
                self.assertTypeEquivalent(left_field.type, right_field.type)
        else:
            self.assertEqual(left, right)

    def test_boolean(self) -> None:
        self.assertEqual(bool, as_type({"type": "boolean"}))
        self.assertEqual(Literal[True], as_type({"type": "boolean", "const": True}))

    def test_integer(self) -> None:
        self.assertEqual(int16, as_type({"type": "integer", "format": "int16"}))
        self.assertEqual(int32, as_type({"type": "integer", "format": "int32"}))
        self.assertEqual(int64, as_type({"type": "integer", "format": "int64"}))
        self.assertEqual(Literal[23], as_type({"type": "integer", "const": 23}))

    def test_number(self) -> None:
        self.assertEqual(float64, as_type({"type": "number", "format": "float64"}))
        self.assertEqual(float, as_type({"type": "number"}))
        self.assertEqual(
            Annotated[Decimal, Precision(5, 2)],
            as_type(
                {
                    "type": "number",
                    "multipleOf": 0.01,
                    "exclusiveMinimum": -1000,
                    "exclusiveMaximum": 1000,
                }
            ),
        )

    def test_string(self) -> None:
        self.assertEqual(str, as_type({"type": "string"}))
        self.assertEqual(
            Literal["value"], as_type({"type": "string", "const": "value"})
        )
        self.assertEqual(
            Annotated[str, MaxLength(10)], as_type({"type": "string", "maxLength": 10})
        )

    def test_integer_enum(self) -> None:
        self.assertEqual(int16, as_type({"type": "integer", "enum": [100, 200]}))
        self.assertEqual(int32, as_type({"type": "integer", "enum": [-32769, 100]}))
        self.assertEqual(int64, as_type({"type": "integer", "enum": [-1, 2147483648]}))

    def test_string_enum(self) -> None:
        enum_type = as_type({"type": "string", "enum": ["first", "second"]})
        if not is_type_enum(enum_type):
            self.fail()

        self.assertCountEqual(["first", "second"], [e.value for e in enum_type])

    def test_date_time(self) -> None:
        self.assertEqual(
            datetime.datetime, as_type({"type": "string", "format": "date-time"})
        )

    def test_uuid(self) -> None:
        self.assertEqual(uuid.UUID, as_type({"type": "string", "format": "uuid"}))

    def test_ipaddress(self) -> None:
        self.assertEqual(
            ipaddress.IPv4Address, as_type({"type": "string", "format": "ipv4"})
        )
        self.assertEqual(
            ipaddress.IPv6Address, as_type({"type": "string", "format": "ipv6"})
        )

    def test_object(self) -> None:
        self.assertEqual(JsonType, as_type({"type": "object"}))

    def test_array(self) -> None:
        self.assertEqual(
            List[str], as_type({"type": "array", "items": {"type": "string"}})
        )

    def test_dataclass(self) -> None:
        schema = classdef_to_schema(Person)
        self.assertTypeEquivalent(
            Person, schema_to_type(schema, module=empty, class_name="Person")
        )

    def test_oneOf(self) -> None:
        self.assertEqual(str, as_type({"oneOf": [{"type": "string"}]}))
        self.assertEqual(
            Union[str, int],
            as_type({"oneOf": [{"type": "string"}, {"type": "integer"}]}),
        )

        self.assertTypeEquivalent(
            UnionOfValues,
            schema_to_type(
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "value": {
                            "oneOf": [{"type": "string"}, {"type": "integer"}],
                        }
                    },
                    "additionalProperties": False,
                },
                module=empty,
                class_name=UnionOfValues.__name__,
            ),
        )

        self.assertTypeEquivalent(
            UnionOfAddresses,
            schema_to_type(
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "definitions": {
                        "IPv4Addr": {"type": "string", "format": "ipv4"},
                        "IPv6Addr": {"type": "string", "format": "ipv6"},
                    },
                    "type": "object",
                    "properties": {
                        "address": {
                            "oneOf": [
                                {"$ref": "#/definitions/IPv4Addr"},
                                {"$ref": "#/definitions/IPv6Addr"},
                            ],
                        }
                    },
                    "additionalProperties": False,
                    "required": ["address"],
                },
                module=empty,
                class_name=UnionOfAddresses.__name__,
            ),
        )
        self.assertIsNotNone(getattr(empty, "IPv4Addr", None))
        self.assertIsNotNone(getattr(empty, "IPv6Addr", None))


if __name__ == "__main__":
    unittest.main()
