import dataclasses
import datetime
import decimal
import enum
import functools
import inspect
import json
import typing
import uuid
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, Union

import jsonschema
from jsonschema.exceptions import ValidationError

from .auxiliary import (
    IntegerRange,
    MaxLength,
    MinLength,
    Precision,
    get_auxiliary_format,
    python_type_to_name,
)
from .core import JsonArray, JsonObject, JsonType, Schema
from .inspection import (
    get_class_properties,
    is_type_enum,
    is_type_optional,
    unwrap_optional_type,
)
from .serialization import object_to_json

# determines the maximum number of distinct enum members up to which a Dict[EnumType, Any] is converted into a JSON
# schema with explicitly listed properties (rather than employing a pattern constraint on property names)
OBJECT_ENUM_EXPANSION_LIMIT = 4

try:
    import docstring_parser

    def get_class_docstrings(typ: Type) -> Tuple[Optional[str], Optional[str]]:
        docstring: docstring_parser.Docstring = docstring_parser.parse(typ.__doc__)
        return docstring.short_description, docstring.long_description

    def get_class_property_docstrings(typ: Type) -> Dict[str, str]:
        result = {}
        for base in reversed(inspect.getmro(typ)):
            docstring: docstring_parser.Docstring = docstring_parser.parse(base.__doc__)
            result.update(
                {param.arg_name: param.description for param in docstring.params}
            )
        return result


except ImportError:

    def get_class_property_docstrings(typ: Type) -> Dict[str, str]:
        return {}

    def get_class_docstrings(typ: Type) -> Tuple[Optional[str], Optional[str]]:
        return None, None


def docstring_to_schema(typ: Type) -> Schema:
    short_description, long_description = get_class_docstrings(typ)
    schema = dict()
    if short_description:
        schema["title"] = short_description
    if long_description:
        schema["description"] = long_description
    return schema


class _TypeCatalogAuto:
    "Marker object for a type whose schema is automatically generated on the fly."


_TypeCatalogSchema = Union[Schema, _TypeCatalogAuto]


class TypeCatalog:
    AUTO = _TypeCatalogAuto()

    type_to_schema: Dict[Type, _TypeCatalogSchema]
    type_to_identifier: Dict[Type, str]

    def __init__(self):
        self.type_to_schema = {}
        self.type_to_identifier = {}

    def __contains__(self, typ: Type) -> bool:
        return typ in self.type_to_schema

    def add(self, typ: Type, schema: _TypeCatalogSchema, identifier: str) -> None:
        if typ in self.type_to_schema:
            raise ValueError(f"type {typ} is already registered in the catalog")

        self.type_to_schema[typ] = schema
        self.type_to_identifier[typ] = identifier

    def get_schema(self, typ: Type) -> _TypeCatalogSchema:
        return self.type_to_schema[typ]

    def get_identifier(self, typ: Type) -> str:
        return self.type_to_identifier[typ]


@dataclasses.dataclass
class SchemaOptions:
    definitions_path: str = "#/definitions/"
    use_descriptions: bool = True


class JsonSchemaGenerator:
    """Creates a JSON schema with user-defined type definitions."""

    type_catalog: ClassVar[TypeCatalog] = TypeCatalog()
    types_used: Dict[str, Type]
    options: SchemaOptions

    def __init__(self, options: SchemaOptions = None):
        if options is None:
            self.options = SchemaOptions
        else:
            self.options = options
        self.types_used = {}

    @functools.singledispatchmethod
    def metadata_to_schema(self, arg) -> Schema:
        # unrecognized annotation
        return {}

    @metadata_to_schema.register
    def _(self, arg: IntegerRange) -> Schema:
        return {"minimum": arg.minimum, "maximum": arg.maximum}

    @metadata_to_schema.register
    def _(self, arg: Precision) -> Schema:
        return {
            "multipleOf": 10 ** (-arg.decimal_digits),
            "exclusiveMinimum": -(10 ** arg.integer_digits),
            "exclusiveMaximum": (10 ** arg.integer_digits),
        }

    @metadata_to_schema.register
    def _(self, arg: MinLength) -> Schema:
        return {"minLength": arg.value}

    @metadata_to_schema.register
    def _(self, arg: MaxLength) -> Schema:
        return {"maxLength": arg.value}

    def _with_metadata(
        self, type_schema: Schema, metadata: Optional[Tuple[Any, ...]]
    ) -> Schema:
        if metadata:
            for m in metadata:
                type_schema.update(self.metadata_to_schema(m))
        return type_schema

    def simple_type_to_schema(self, typ: Type) -> Schema:
        "Returns the JSON schema associated with a simple, unrestricted type."

        if typ is None:
            return {"type": "null"}
        elif typ is bool:
            return {"type": "boolean"}
        elif typ is int:
            return {"type": "integer"}
        elif typ is float:
            return {"type": "number"}
        elif typ is str:
            return {"type": "string"}
        elif typ is bytes:
            return {"type": "string", "contentEncoding": "base64"}
        elif typ is datetime.datetime:
            # 2018-11-13T20:20:39+00:00
            return {
                "type": "string",
                "format": "date-time",
            }
        elif typ is datetime.date:
            # 2018-11-13
            return {"type": "string", "format": "date"}
        elif typ is datetime.time:
            # 20:20:39+00:00
            return {"type": "string", "format": "time"}
        elif typ is decimal.Decimal:
            return {"type": "number"}
        elif typ is uuid.UUID:
            # f81d4fae-7dec-11d0-a765-00a0c91e6bf6
            return {"type": "string", "format": "uuid"}
        elif typ is Any:
            return {
                "anyOf": [
                    {"type": "null"},
                    {"type": "boolean"},
                    {"type": "number"},
                    {"type": "string"},
                    {"type": "array"},
                    {"type": "object"},
                ]
            }
        elif typ is JsonObject:
            return {"type": "object"}
        elif typ is JsonArray:
            return {"type": "array"}
        else:
            # not a simple type
            return None

    def type_to_schema(self, data_type: Type, force_expand: bool = False) -> Schema:
        """
        Returns the JSON schema associated with a type.

        :param data_type: The Python type whose JSON schema to return.
        :param force_expand: Forces a JSON schema to be returned even if the type is registered in the catalog of known types.
        """

        # short-circuit for common simple types
        schema = self.simple_type_to_schema(data_type)
        if schema is not None:
            return schema

        # short-circuit with an error message when passing invalid data
        if isinstance(data_type, str):
            raise TypeError(f"object is not a type but a string")

        # types registered in the type catalog of well-known types
        if not force_expand and data_type in __class__.type_catalog:
            # user-defined type
            identifier = __class__.type_catalog.get_identifier(data_type)
            self.types_used[identifier] = data_type
            return {"$ref": f"{self.options.definitions_path}{identifier}"}

        # unwrap annotated types
        metadata = getattr(data_type, "__metadata__", None)
        if metadata is not None:
            # type is Annotated[T, ...]
            typ = typing.get_args(data_type)[0]

            schema = self.simple_type_to_schema(typ)
            if schema is not None:
                # recognize well-known auxiliary types
                fmt = get_auxiliary_format(data_type)
                if fmt is not None:
                    schema.update({"format": fmt})
                    return schema
                else:
                    return self._with_metadata(schema, metadata)

        else:
            # type is a regular type
            typ = data_type

        if isinstance(typ, typing.ForwardRef):
            fwd: typing.ForwardRef = typ
            identifier = fwd.__forward_arg__
            typ = eval(identifier)
            self.types_used[identifier] = typ
            return {"$ref": f"{self.options.definitions_path}{identifier}"}

        if is_type_enum(typ):
            enum_type: Type[enum.Enum] = typ
            enum_values = [e.value for e in enum_type]
            enum_value_types = list(dict.fromkeys(type(value) for value in enum_values))
            if len(enum_value_types) != 1:
                raise ValueError(
                    f"enumerations must have a consistent member value type but several types found: {enum_value_types}"
                )

            enum_value_type = enum_value_types[0]
            if enum_value_type is bool:
                enum_schema_type = "boolean"
            elif enum_value_type is int:
                enum_schema_type = "integer"
            elif enum_value_type is float:
                enum_schema_type = "number"
            elif enum_value_type is str:
                enum_schema_type = "string"
            else:
                raise ValueError(
                    f"unsupported enumeration member value type: {enum_value_type}"
                )

            enum_schema = {"type": enum_schema_type, "enum": enum_values}
            if self.options.use_descriptions:
                enum_schema.update(docstring_to_schema(typ))
            return enum_schema

        origin_type = typing.get_origin(typ)
        if origin_type is list:
            (list_type,) = typing.get_args(typ)  # unpack single tuple element
            return {"type": "array", "items": self.type_to_schema(list_type)}
        elif origin_type is dict:
            key_type, value_type = typing.get_args(typ)
            if not (key_type is str or key_type is int or is_type_enum(key_type)):
                raise ValueError(
                    "`dict` with key type not coercible to `str` is not supported"
                )

            value_schema = self.type_to_schema(value_type)
            if is_type_enum(key_type):
                enum_values = [e.value for e in key_type]
                if len(enum_values) > OBJECT_ENUM_EXPANSION_LIMIT:
                    dict_schema = {
                        "propertyNames": {
                            "pattern": "^(" + "|".join(enum_values) + ")$"
                        },
                        "additionalProperties": value_schema,
                    }
                else:
                    dict_schema = {
                        "properties": dict(
                            (str(value), value_schema) for value in enum_values
                        ),
                        "additionalProperties": False,
                    }
            else:
                dict_schema = {"additionalProperties": value_schema}

            schema = {"type": "object"}
            schema.update(dict_schema)
            return schema
        elif origin_type is set:
            (set_type,) = typing.get_args(typ)  # unpack single tuple element
            return {
                "type": "array",
                "items": self.type_to_schema(set_type),
                "uniqueItems": True,
            }
        elif origin_type is tuple:
            args = typing.get_args(typ)
            return {
                "type": "array",
                "minItems": len(args),
                "maxItems": len(args),
                "prefixItems": [
                    self.type_to_schema(member_type) for member_type in args
                ],
            }
        elif origin_type is type:
            (concrete_type,) = typing.get_args(typ)  # unpack single tuple element
            return {"const": self.type_to_schema(concrete_type, force_expand=True)}
        elif origin_type is Union:
            return {
                "oneOf": [
                    self.type_to_schema(union_type)
                    for union_type in typing.get_args(typ)
                ]
            }

        # dictionary of class attributes
        members = dict(inspect.getmembers(typ, lambda a: not inspect.isroutine(a)))

        property_docstrings = get_class_property_docstrings(typ)

        properties: Dict[str, Schema] = {}
        required: List[Schema] = []
        for property_name, property_type in get_class_properties(typ):
            if is_type_optional(property_type):
                optional_type = unwrap_optional_type(property_type)
                property_def = self.type_to_schema(optional_type)
            else:
                property_def = self.type_to_schema(property_type)
                required.append(property_name)

            # check if attribute has a default value initializer
            if members.get(property_name) is not None:
                def_value = members[property_name]
                # check if value can be directly represented in JSON
                if isinstance(
                    def_value,
                    (
                        bool,
                        int,
                        float,
                        str,
                        enum.Enum,
                        datetime.datetime,
                        datetime.date,
                        datetime.time,
                    ),
                ):
                    property_def["default"] = object_to_json(def_value)

            # add property docstring if available
            property_doc = property_docstrings.get(property_name)
            if property_doc:
                property_def["title"] = property_doc
                property_def.pop("description", None)

            properties[property_name] = property_def

        schema = {"type": "object"}
        if len(properties) > 0:
            schema["properties"] = properties
            schema["additionalProperties"] = False
        if len(required) > 0:
            schema["required"] = required
        if self.options.use_descriptions:
            schema.update(docstring_to_schema(typ))
        return schema

    def _classdef_to_schema(self, subtype: Type) -> Schema:
        "Returns the JSON schema associated with a type that may be registered in the catalog of known types."

        subschema = __class__.type_catalog.get_schema(subtype)
        if subschema is _TypeCatalogAuto:
            type_schema = self.type_to_schema(subtype, force_expand=True)
        else:
            type_schema = subschema.copy()

            # add descriptive text (if present)
            if self.options.use_descriptions:
                type_schema.update(docstring_to_schema(subtype))

        return type_schema

    def classdef_to_schema(
        self, typ: Type, force_expand: bool = False
    ) -> Tuple[Schema, Dict[str, Schema]]:
        """
        Returns the JSON schema associated with a type and any nested types.

        :param typ: The type whose JSON schema to return.
        :return: A tuple of the JSON schema, and a mapping between nested type names and their corresponding schema.
        """

        self.types_used = {}
        try:
            type_schema = self.type_to_schema(typ, force_expand=force_expand)

            types_defined = {}
            while len(self.types_used) > len(types_defined):
                # make a snapshot copy; original collection is going to be modified
                types_undefined = {
                    sub_name: sub_type
                    for sub_name, sub_type in self.types_used.items()
                    if sub_name not in types_defined
                }

                # expand undefined types, which may lead to additional types to be defined
                for sub_name, sub_type in types_undefined.items():
                    types_defined[sub_name] = self._classdef_to_schema(sub_type)

            type_definitions = dict(sorted(types_defined.items()))
        finally:
            self.types_used = {}

        return type_schema, type_definitions


def classdef_to_schema(typ: Type, options: SchemaOptions = None) -> Schema:
    """
    Returns the JSON schema corresponding to the given type.

    :param typ: The Python type used to generate the JSON schema
    :return: A JSON object that you can serialize to a JSON string with json.dump or json.dumps
    """

    type_schema, type_definitions = JsonSchemaGenerator(options).classdef_to_schema(typ)

    schema = {"$schema": "http://json-schema.org/draft-07/schema#"}
    if type_definitions:
        schema["definitions"] = type_definitions
    schema.update(type_schema)
    return schema


def validate_object(object_type: Type, json_dict: JsonType) -> None:
    """
    Validates if the JSON dictionary object conforms to the expected type.

    :param object_type: The type to match against
    :param json_dict: A JSON object obtained with json.load or json.loads
    :raises ValidationError: Indicates that the JSON object cannot represent the type.
    """

    schema_dict = classdef_to_schema(object_type)
    jsonschema.validate(
        json_dict, schema_dict, format_checker=jsonschema.FormatChecker()
    )


def print_schema(typ: Type) -> None:
    """Pretty-prints the JSON schema corresponding to the type."""

    s = classdef_to_schema(typ)
    print(json.dumps(s, indent=4))


def register_schema(typ: Type, schema: Schema = None, name: str = None):
    JsonSchemaGenerator.type_catalog.add(
        typ,
        schema if schema is not None else _TypeCatalogAuto,
        name if name is not None else python_type_to_name(typ),
    )
    return typ


def json_schema_type(cls=None, /, *, schema=None):
    """Decorator to add user-defined schema definition to a class."""

    def wrap(cls):
        return register_schema(cls, schema)

    # see if decorator is used as @json_schema_type or @json_schema_type()
    if cls is None:
        # called with parentheses
        return wrap
    else:
        # called as @json_schema_type without parentheses
        return wrap(cls)


register_schema(JsonType, name="JsonType")
register_schema(JsonObject, name="JsonObject")
register_schema(JsonArray, name="JsonArray")
