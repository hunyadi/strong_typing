from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Annotated, Literal

from strong_typing.auxiliary import Alias
from strong_typing.schema import JsonSchemaGenerator, SchemaOptions
from strong_typing.serialization import json_to_object, object_to_json


@dataclass
class DeferredAlpha:
    kind: Literal["alpha"]
    value: int


@dataclass
class DeferredBeta:
    kind: Literal["beta"]
    value: int


@dataclass
class DeferredChild:
    count: int


@dataclass
class DeferredDocument:
    display_name: Annotated[str, Alias("displayName")]
    child: DeferredChild
    optional_count: int | None


class TestDeferredAnnotations(unittest.TestCase):
    def test_annotations_are_deferred(self) -> None:
        "Verifies if `from __future__ import annotations` is in effect by checking if the annotation is a string."

        self.assertEqual(DeferredDocument.__annotations__["child"], "DeferredChild")

    def test_tagged_union(self) -> None:
        self.assertEqual(
            json_to_object(DeferredAlpha | DeferredBeta, {"kind": "beta", "value": 3}),
            DeferredBeta(kind="beta", value=3),
        )

    def test_schema_generation(self) -> None:
        schema = JsonSchemaGenerator(SchemaOptions(use_descriptions=False)).type_to_schema(
            DeferredDocument, force_expand=True
        )

        self.assertEqual(
            schema,
            {
                "type": "object",
                "properties": {
                    "displayName": {"type": "string"},
                    "child": {
                        "type": "object",
                        "properties": {"count": {"type": "integer"}},
                        "additionalProperties": False,
                        "required": ["count"],
                    },
                    "optional_count": {"type": "integer"},
                },
                "additionalProperties": False,
                "required": ["displayName", "child"],
            },
        )

    def test_serialization(self) -> None:
        self.assertEqual(
            object_to_json(DeferredDocument("sample", DeferredChild(3), None)),
            {"displayName": "sample", "child": {"count": 3}},
        )
