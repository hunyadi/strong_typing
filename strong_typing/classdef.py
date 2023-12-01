import copy
import dataclasses
import datetime
import decimal
import enum
import ipaddress
import math
import re
import types
import typing
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple, Type, TypeVar, Union

from .auxiliary import (
    Alias,
    Annotated,
    MaxLength,
    Precision,
    float32,
    float64,
    int16,
    int32,
    int64,
)
from .core import JsonType, Schema
from .docstring import Docstring, DocstringParam
from .inspection import TypeLike
from .serialization import json_to_object, object_to_json

T = TypeVar("T")


@dataclass
class JsonSchemaNode:
    title: Optional[str]
    description: Optional[str]


@dataclass
class JsonSchemaType(JsonSchemaNode):
    type: str
    format: Optional[str]


@dataclass
class JsonSchemaBoolean(JsonSchemaType):
    type: Literal["boolean"]
    const: Optional[bool]
    examples: Optional[List[bool]]


@dataclass
class JsonSchemaInteger(JsonSchemaType):
    type: Literal["integer"]
    const: Optional[int]
    examples: Optional[List[int]]
    enum: Optional[List[int]]
    minimum: Optional[int]
    maximum: Optional[int]


@dataclass
class JsonSchemaNumber(JsonSchemaType):
    type: Literal["number"]
    const: Optional[float]
    examples: Optional[List[float]]
    minimum: Optional[float]
    maximum: Optional[float]
    exclusiveMinimum: Optional[float]
    exclusiveMaximum: Optional[float]
    multipleOf: Optional[float]


@dataclass
class JsonSchemaString(JsonSchemaType):
    type: Literal["string"]
    const: Optional[str]
    examples: Optional[List[str]]
    enum: Optional[List[str]]
    minLength: Optional[int]
    maxLength: Optional[int]


@dataclass
class JsonSchemaArray(JsonSchemaType):
    type: Literal["array"]
    items: "JsonSchemaAny"


@dataclass
class JsonSchemaObject(JsonSchemaType):
    type: Literal["object"]
    properties: Optional[Dict[str, "JsonSchemaAny"]]
    additionalProperties: Optional[bool]
    required: Optional[List[str]]


@dataclass
class JsonSchemaRef(JsonSchemaNode):
    ref: Annotated[str, Alias("$ref")]


@dataclass
class JsonSchemaAllOf(JsonSchemaNode):
    allOf: List["JsonSchemaAny"]


@dataclass
class JsonSchemaAnyOf(JsonSchemaNode):
    anyOf: List["JsonSchemaAny"]


@dataclass
class JsonSchemaOneOf(JsonSchemaNode):
    oneOf: List["JsonSchemaAny"]


JsonSchemaAny = Union[
    JsonSchemaRef,
    JsonSchemaBoolean,
    JsonSchemaInteger,
    JsonSchemaNumber,
    JsonSchemaString,
    JsonSchemaArray,
    JsonSchemaObject,
    JsonSchemaOneOf,
]


@dataclass
class JsonSchemaTopLevelObject(JsonSchemaObject):
    schema: Annotated[str, Alias("$schema")]
    definitions: Optional[Dict[str, JsonSchemaAny]]


def integer_range_to_type(min_value: float, max_value: float) -> type:
    if min_value >= -(2**15) and max_value < 2**15:
        return int16
    elif min_value >= -(2**31) and max_value < 2**31:
        return int32
    else:
        return int64


def enum_safe_name(name: str) -> str:
    return re.sub(r"\W", "_", name)


def enum_values_to_type(
    module: types.ModuleType,
    name: str,
    values: Dict[str, Any],
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> Type[enum.Enum]:
    enum_class: Type[enum.Enum] = enum.Enum(name, values)  # type: ignore

    # assign the newly created type to the same module where the defining class is
    enum_class.__module__ = module.__name__
    enum_class.__doc__ = str(
        Docstring(short_description=title, long_description=description)
    )
    setattr(module, name, enum_class)

    return enum.unique(enum_class)


def schema_to_type(
    schema: Schema, *, module: types.ModuleType, class_name: str
) -> TypeLike:
    """
    Creates a Python type from a JSON schema.

    :param schema: The JSON schema that the types would correspond to.
    :param module: The module in which to create the new types.
    :param class_name: The name assigned to the top-level class.
    """

    top_node = typing.cast(
        JsonSchemaTopLevelObject, json_to_object(JsonSchemaTopLevelObject, schema)
    )
    if top_node.definitions is not None:
        for type_name, type_node in top_node.definitions.items():
            def_type = node_to_type(module, type_name, type_node)
            setattr(def_type, "__module__", module.__name__)
            setattr(module, type_name, def_type)

    return node_to_type(module, class_name, top_node)


def node_to_type(
    module: types.ModuleType, context: str, node: JsonSchemaNode
) -> TypeLike:
    if isinstance(node, JsonSchemaRef):
        match_obj = re.match(r"^#/definitions/(\w+)$", node.ref)
        if not match_obj:
            raise ValueError(f"invalid reference: {node.ref}")

        type_name = match_obj.group(1)
        return getattr(module, type_name)

    elif isinstance(node, JsonSchemaBoolean):
        if node.const is not None:
            return Literal[node.const]

        return bool

    elif isinstance(node, JsonSchemaInteger):
        if node.const is not None:
            return Literal[node.const]

        if node.format == "int16":
            return int16
        elif node.format == "int32":
            return int32
        elif node.format == "int64":
            return int64

        if node.enum is not None:
            return integer_range_to_type(min(node.enum), max(node.enum))

        if node.minimum is not None and node.maximum is not None:
            return integer_range_to_type(node.minimum, node.maximum)

        return int

    elif isinstance(node, JsonSchemaNumber):
        if node.const is not None:
            return Literal[node.const]

        if node.format == "float32":
            return float32
        elif node.format == "float64":
            return float64

        if (
            node.exclusiveMinimum is not None
            and node.exclusiveMaximum is not None
            and node.exclusiveMinimum == -node.exclusiveMaximum
        ):
            integer_digits = round(math.log10(node.exclusiveMaximum))
        else:
            integer_digits = None

        if node.multipleOf is not None:
            decimal_digits = -round(math.log10(node.multipleOf))
        else:
            decimal_digits = None

        if integer_digits is not None and decimal_digits is not None:
            return Annotated[
                decimal.Decimal,
                Precision(integer_digits + decimal_digits, decimal_digits),
            ]

        return float

    elif isinstance(node, JsonSchemaString):
        if node.const is not None:
            return Literal[node.const]

        if node.format == "date-time":
            return datetime.datetime
        elif node.format == "uuid":
            return uuid.UUID
        elif node.format == "ipv4":
            return ipaddress.IPv4Address
        elif node.format == "ipv6":
            return ipaddress.IPv6Address

        if node.enum is not None:
            return enum_values_to_type(
                module,
                context,
                {enum_safe_name(e): e for e in node.enum},
                title=node.title,
                description=node.description,
            )

        if node.maxLength is not None:
            return Annotated[str, MaxLength(node.maxLength)]

        return str

    elif isinstance(node, JsonSchemaArray):
        return List[node_to_type(module, context, node.items)]  # type: ignore

    elif isinstance(node, JsonSchemaObject):
        if node.properties is None:
            return JsonType

        if node.additionalProperties is None or node.additionalProperties is not False:
            raise TypeError("expected: `additionalProperties` equals `false`")

        required = node.required if node.required is not None else []

        class_name = context

        fields: List[Tuple[str, Any]] = []
        params: Dict[str, DocstringParam] = {}
        for prop_name, prop_node in node.properties.items():
            typ = node_to_type(module, f"{class_name}__{prop_name}", prop_node)
            if prop_name in required:
                prop_type = typ
            else:
                prop_type = Union[(None, typ)]
            fields.append((prop_name, prop_type))
            prop_desc = prop_node.title or prop_node.description
            if prop_desc is not None:
                params[prop_name] = DocstringParam(prop_name, prop_desc)

        class_type = dataclasses.make_dataclass(
            class_name, fields, namespace={"__module__": module.__name__}
        )
        class_type.__doc__ = str(
            Docstring(
                short_description=node.title,
                long_description=node.description,
                params=params,
            )
        )
        setattr(module, class_name, class_type)
        return class_type

    elif isinstance(node, JsonSchemaOneOf):
        union_types = tuple(node_to_type(module, context, n) for n in node.oneOf)
        return Union[union_types]

    raise NotImplementedError()


@dataclass
class SchemaFlatteningOptions:
    qualified_names: bool = False
    recursive: bool = False


def flatten_schema(
    schema: Schema, *, options: Optional[SchemaFlatteningOptions] = None
) -> Schema:
    top_node = typing.cast(
        JsonSchemaTopLevelObject, json_to_object(JsonSchemaTopLevelObject, schema)
    )
    flattener = SchemaFlattener(options)
    obj = flattener.flatten(top_node)
    return typing.cast(Schema, object_to_json(obj))


class SchemaFlattener:
    options: SchemaFlatteningOptions

    def __init__(self, options: Optional[SchemaFlatteningOptions] = None) -> None:
        self.options = options or SchemaFlatteningOptions()

    def flatten(self, source_node: JsonSchemaObject) -> JsonSchemaObject:
        if source_node.type != "object":
            return source_node

        source_props = source_node.properties or {}
        target_props: Dict[str, JsonSchemaAny] = {}

        source_reqs = source_node.required or []
        target_reqs: List[str] = []

        for name, prop in source_props.items():
            if not isinstance(prop, JsonSchemaObject):
                target_props[name] = prop
                if name in source_reqs:
                    target_reqs.append(name)
                continue

            if self.options.recursive:
                obj = self.flatten(prop)
            else:
                obj = prop
            if obj.properties is not None:
                if self.options.qualified_names:
                    target_props.update(
                        (f"{name}.{n}", p) for n, p in obj.properties.items()
                    )
                else:
                    target_props.update(obj.properties.items())
            if obj.required is not None:
                if self.options.qualified_names:
                    target_reqs.extend(f"{name}.{n}" for n in obj.required)
                else:
                    target_reqs.extend(obj.required)

        target_node = copy.copy(source_node)
        target_node.properties = target_props or None
        target_node.additionalProperties = False
        target_node.required = target_reqs or None
        return target_node
