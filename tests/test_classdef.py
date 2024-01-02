import datetime
import ipaddress
import typing
import unittest
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Literal, Optional, Union

from strong_typing.auxiliary import (
    Annotated,
    MaxLength,
    Precision,
    float64,
    int16,
    int32,
    int64,
)
from strong_typing.classdef import (
    JsonSchemaAny,
    SchemaFlatteningOptions,
    TypeDef,
    flatten_schema,
    node_to_typedef,
    schema_to_type,
)
from strong_typing.core import JsonType, Schema
from strong_typing.inspection import (
    TypeLike,
    create_module,
    dataclass_fields,
    is_dataclass_type,
    is_type_enum,
)
from strong_typing.schema import classdef_to_schema
from strong_typing.serialization import json_to_object

empty = create_module("empty")


def as_typedef(schema: Schema) -> TypeDef:
    node = typing.cast(
        JsonSchemaAny, json_to_object(JsonSchemaAny, schema, context=empty)
    )
    return node_to_typedef(empty, "", node)


def as_type(schema: Schema) -> TypeLike:
    return as_typedef(schema).type


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
        enum_type = as_type(
            {"type": "string", "enum": ["first", "second", "_sunder_", "__dunder"]}
        )
        if not is_type_enum(enum_type):
            self.fail()

        self.assertCountEqual(
            ["first", "second", "_sunder_", "__dunder"], [e.value for e in enum_type]
        )

    def test_date_time(self) -> None:
        self.assertEqual(
            datetime.datetime, as_type({"type": "string", "format": "date-time"})
        )
        self.assertEqual(
            datetime.datetime,
            as_type(
                {
                    "type": "string",
                    "format": "date-time",
                    "title": "Date and time together",
                    "description": (
                        "Date and time together, as represented in RFC 3339, section 5.6. "
                        "This is a subset of the date format also commonly known as ISO 8601 format."
                    ),
                    "examples": ["2018-11-13T20:20:39+00:00"],
                }
            ),
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
        self.assertEqual(
            ipaddress.IPv4Address,
            as_type(
                {
                    "type": "string",
                    "format": "ipv4",
                    "title": "Represent and manipulate single IPv4 Addresses.",
                    "description": "IPv4 address, according to dotted-quad ABNF syntax as defined in RFC 2673, section 3.2.",
                    "examples": ["192.0.2.0", "198.51.100.1", "203.0.113.255"],
                }
            ),
        )

    def test_object(self) -> None:
        self.assertEqual(JsonType, as_type({"type": "object"}))

    def test_array(self) -> None:
        self.assertEqual(
            List[str], as_type({"type": "array", "items": {"type": "string"}})
        )

    def test_default(self) -> None:
        self.assertEqual(
            TypeDef(bool, True),
            as_typedef({"type": "boolean", "default": True}),
        )
        self.assertEqual(
            TypeDef(int, 23),
            as_typedef({"type": "integer", "default": 23}),
        )
        self.assertEqual(
            TypeDef(
                datetime.datetime,
                datetime.datetime(1989, 10, 23, 1, 2, 3, tzinfo=datetime.timezone.utc),
            ),
            as_typedef(
                {
                    "type": "string",
                    "format": "date-time",
                    "default": "1989-10-23T01:02:03Z",
                }
            ),
        )
        self.assertEqual(
            TypeDef(ipaddress.IPv4Address, ipaddress.IPv4Address("192.0.2.0")),
            as_typedef({"type": "string", "format": "ipv4", "default": "192.0.2.0"}),
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

    def test_flatten(self) -> None:
        source: Schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "meta": {
                    "type": "object",
                    "properties": {
                        "ts": {"type": "string", "format": "date-time"},
                        "action": {
                            "type": "string",
                            "enum": ["U", "D"],
                        },
                    },
                    "additionalProperties": False,
                    "required": ["ts"],
                },
                "key": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "format": "int64",
                        }
                    },
                    "additionalProperties": False,
                    "required": ["id"],
                },
                "value": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "maxLength": 255,
                            "description": "Display name.",
                        },
                        "created_at": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Timestamp of when the record was created.",
                        },
                        "updated_at": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Timestamp of when the record was updated.",
                        },
                        "nested": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "integer",
                                    "format": "int64",
                                }
                            },
                            "additionalProperties": False,
                            "required": ["id"],
                        },
                    },
                    "additionalProperties": False,
                    "required": ["created_at", "updated_at"],
                },
            },
            "additionalProperties": False,
            "required": ["key"],
        }

        target: Schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "meta.ts": {"type": "string", "format": "date-time"},
                "meta.action": {"type": "string", "enum": ["U", "D"]},
                "key.id": {"type": "integer", "format": "int64"},
                "value.name": {
                    "description": "Display name.",
                    "type": "string",
                    "maxLength": 255,
                },
                "value.created_at": {
                    "description": "Timestamp of when the record was created.",
                    "type": "string",
                    "format": "date-time",
                },
                "value.updated_at": {
                    "description": "Timestamp of when the record was updated.",
                    "type": "string",
                    "format": "date-time",
                },
                "value.nested.id": {
                    "type": "integer",
                    "format": "int64",
                },
            },
            "additionalProperties": False,
            "required": [
                "meta.ts",
                "key.id",
                "value.created_at",
                "value.updated_at",
                "value.nested.id",
            ],
        }
        self.assertEqual(
            flatten_schema(
                source,
                options=SchemaFlatteningOptions(qualified_names=True, recursive=True),
            ),
            target,
        )

        target = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "ts": {"type": "string", "format": "date-time"},
                "action": {"type": "string", "enum": ["U", "D"]},
                "id": {"type": "integer", "format": "int64"},
                "name": {
                    "description": "Display name.",
                    "type": "string",
                    "maxLength": 255,
                },
                "created_at": {
                    "description": "Timestamp of when the record was created.",
                    "type": "string",
                    "format": "date-time",
                },
                "updated_at": {
                    "description": "Timestamp of when the record was updated.",
                    "type": "string",
                    "format": "date-time",
                },
                "nested": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "format": "int64",
                        }
                    },
                    "additionalProperties": False,
                    "required": ["id"],
                },
            },
            "additionalProperties": False,
            "required": ["ts", "id", "created_at", "updated_at"],
        }
        self.assertEqual(
            flatten_schema(
                source,
                options=SchemaFlatteningOptions(qualified_names=False, recursive=False),
            ),
            target,
        )


if __name__ == "__main__":
    unittest.main()
