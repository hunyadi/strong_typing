import datetime
import decimal
import unittest
import uuid
from typing import Any, Dict, List, Set, Tuple, Union

from test_sample_types import (
    UID,
    AnnotatedSimpleDataclass,
    BinaryTree,
    Side,
    SimpleDataclass,
    SimpleTypedNamedTuple,
    SimpleValueWrapper,
    Suit,
    ValueExample,
)

from strong_typing.auxiliary import Annotated, IntegerRange, Precision, int32, uint64
from strong_typing.core import JsonType
from strong_typing.schema import (
    JsonSchemaGenerator,
    JsonType,
    SchemaOptions,
    Validator,
    classdef_to_schema,
    get_class_docstrings,
)


class TestSchema(unittest.TestCase):
    def test_schema(self) -> None:
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
            generator.type_to_schema(SimpleValueWrapper),
            {
                "type": "object",
                "properties": {"value": {"type": "integer", "default": 23}},
                "additionalProperties": False,
                "required": ["value"],
                "title": "A simple data class with a single property.",
            },
        )
        self.assertEqual(
            generator.type_to_schema(SimpleTypedNamedTuple),
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

    def test_recursive(self) -> None:
        options = SchemaOptions(use_descriptions=False)
        generator = JsonSchemaGenerator(options)
        self.assertEqual(
            generator.type_to_schema(BinaryTree, force_expand=True),
            {
                "type": "object",
                "properties": {
                    "left": {"$ref": "#/definitions/BinaryTree"},
                    "right": {"$ref": "#/definitions/BinaryTree"},
                },
                "additionalProperties": False,
            },
        )

    def test_registered(self) -> None:
        options = SchemaOptions(use_descriptions=False)
        generator = JsonSchemaGenerator(options)
        self.assertEqual(
            generator.type_to_schema(JsonType, force_expand=True),
            {
                "oneOf": [
                    {"type": "null"},
                    {"type": "boolean"},
                    {"type": "integer"},
                    {"type": "number"},
                    {"type": "string"},
                    {
                        "type": "object",
                        "additionalProperties": {"$ref": "#/definitions/JsonType"},
                    },
                    {
                        "type": "array",
                        "items": {"$ref": "#/definitions/JsonType"},
                    },
                ],
            },
        )

        self.assertEqual(
            classdef_to_schema(JsonType, options),
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

    def test_annotated(self) -> None:
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
            generator.type_to_schema(AnnotatedSimpleDataclass),
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

    def test_fixed_width(self) -> None:
        options = SchemaOptions(use_descriptions=True)
        generator = JsonSchemaGenerator(options)
        self.assertEqual(
            generator.type_to_schema(int32), {"format": "int32", "type": "integer"}
        )
        self.assertEqual(
            generator.type_to_schema(uint64), {"format": "uint64", "type": "integer"}
        )

    def _assert_docstring_equal(
        self, generator: JsonSchemaGenerator, typ: type
    ) -> None:
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

    def test_docstring(self) -> None:
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
        self._assert_docstring_equal(generator, SimpleDataclass)


if __name__ == "__main__":
    unittest.main()
