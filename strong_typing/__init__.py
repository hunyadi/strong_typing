"""
Type-safe data interchange for Python data classes.

Provides auxiliary services for working with Python type annotations, converting typed data to and from JSON,
and generating a JSON schema for a complex type.
"""

import base64
import dataclasses
import datetime
import enum
import inspect
import json
import keyword
import re
import types
import typing
import uuid
from typing import (
    Any,
    ClassVar,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import jsonschema
from jsonschema.exceptions import ValidationError

# determines the maximum number of distinct enum members up to which a Dict[EnumType, Any] is converted into a JSON
# schema with explicitly listed properties (rather than employing a pattern constraint on property names)
OBJECT_ENUM_EXPANSION_LIMIT = 4

JsonType = Union[None, bool, int, float, str, Dict[str, "JsonType"], List["JsonType"]]
Schema = JsonType
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


def is_dataclass_type(typ) -> bool:
    "True if the argument corresponds to a data class type (but not an instance)."

    return isinstance(typ, type) and dataclasses.is_dataclass(typ)


def is_dataclass_instance(obj) -> bool:
    "True if the argument corresponds to a data class instance (but not a type)."

    return not isinstance(obj, type) and dataclasses.is_dataclass(obj)


def is_named_tuple_instance(obj) -> bool:
    "True if the argument corresponds to a named tuple instance."

    return is_named_tuple_type(type(obj))


def is_named_tuple_type(typ) -> bool:
    """
    True if the argument corresponds to a named tuple type.

    Calling the function `collections.namedtuple` gives a new type that is a subclass of `tuple` (and no other classes)
    with a member named `_fields` that is a tuple whose items are all strings.
    """

    b = typ.__bases__
    if len(b) != 1 or b[0] != tuple:
        return False

    f = getattr(typ, "_fields", None)
    if not isinstance(f, tuple):
        return False

    return all(type(n) == str for n in f)


def get_module_classes(module: types.ModuleType) -> List[Type]:
    is_class_member = (
        lambda member: inspect.isclass(member) and member.__module__ == module.__name__
    )
    return [class_type for _, class_type in inspect.getmembers(module, is_class_member)]


def get_class_properties(typ: Type) -> Iterable[Tuple[str, Type]]:
    resolved_hints = typing.get_type_hints(typ)

    if is_dataclass_type(typ):
        return (
            (field.name, resolved_hints[field.name])
            for field in dataclasses.fields(typ)
        )
    else:
        return resolved_hints.items()


def python_id_to_json_field(python_id: str) -> str:
    """
    Convert a Python identifier to a JSON field name.

    Authors may use an underscore appended at the end of a Python identifier as per PEP 8 if it clashes with a Python
    keyword: e.g. `in` would become `in_` and `from` would become `from_`. Remove these suffixes when exporting to JSON.
    """

    if python_id.endswith("_"):
        id = python_id[:-1]
        if keyword.iskeyword(id):
            return id

    return python_id


def object_to_json(obj: Any) -> JsonType:
    """
    Convert an object to a representation that can be exported to JSON.
    Fundamental types (e.g. numeric types) are left as is. Objects with properties are converted
    to a dictionaries of key-value pairs.
    """

    # check for well-known types
    if isinstance(obj, (bool, int, float, str)):  # can be directly represented in JSON
        return obj
    elif isinstance(obj, bytes):
        return base64.b64encode(obj).decode("ascii")
    elif isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, enum.Enum):
        return obj.value
    elif isinstance(obj, list):
        return [object_to_json(item) for item in obj]
    elif isinstance(obj, dict):
        if obj and isinstance(next(iter(obj.keys())), enum.Enum):
            generator = (
                (key.value, object_to_json(value)) for key, value in obj.items()
            )
        else:
            generator = (
                (str(key), object_to_json(value)) for key, value in obj.items()
            )
        return dict(generator)
    elif isinstance(obj, set):
        return [object_to_json(item) for item in obj]

    # check if object has custom serialization method
    convert_func = getattr(obj, "to_json", None)
    if callable(convert_func):
        return convert_func()

    if is_dataclass_instance(obj):
        object_dict = {}
        for field in dataclasses.fields(obj):
            value = getattr(obj, field.name)
            if value is None:
                continue
            object_dict[python_id_to_json_field(field.name)] = object_to_json(value)
        return object_dict

    elif is_named_tuple_instance(obj):
        object_dict = {}
        for field in type(obj)._fields:
            value = getattr(obj, field)
            if value is None:
                continue
            object_dict[python_id_to_json_field(field)] = object_to_json(value)
        return object_dict

    elif isinstance(obj, tuple):
        # check plain tuple after named tuple, named tuples are also instances of tuple
        return [object_to_json(item) for item in obj]

    # fail early if caller passes an object with an exotic type
    if (
        inspect.isfunction(obj)
        or inspect.ismodule(obj)
        or inspect.isclass(obj)
        or inspect.ismethod(obj)
    ):
        raise TypeError(f"object of type {type(obj)} cannot be represented in JSON")

    # iterate over object attributes to get a standard representation
    object_dict = {}
    for name in dir(obj):
        # filter built-in and special properties
        if re.match(r"^__.+__$", name):
            continue

        # filter built-in special names
        if name in ["_abc_impl"]:
            continue

        value = getattr(obj, name)
        if value is None:
            continue

        # filter instance methods
        if inspect.ismethod(value):
            continue

        object_dict[python_id_to_json_field(name)] = object_to_json(value)

    return object_dict


def json_to_object(typ: Type[T], data: JsonType) -> T:
    """
    Create an object from a representation that has been de-serialized from JSON.
    Fundamental types (e.g. numeric types) are left as is. Objects with properties are populated
    from dictionaries of key-value pairs using reflection (enumerating instance type annotations).
    """

    # check for well-known types
    if typ is bool or typ is int or typ is float or typ is str:
        return data
    elif typ is bytes:
        return base64.b64decode(data)
    elif typ is datetime.datetime or typ is datetime.date or typ is datetime.time:
        return typ.fromisoformat(data)
    elif typ is uuid.UUID:
        return uuid.UUID(data)

    # generic types (e.g. list, dict, set, etc.)
    origin_type = typing.get_origin(typ)
    if origin_type is list:
        (list_type,) = typing.get_args(typ)  # unpack single tuple element
        return [json_to_object(list_type, item) for item in data]
    elif origin_type is dict:
        key_type, value_type = typing.get_args(typ)
        return dict(
            (key_type(key), json_to_object(value_type, value))
            for key, value in data.items()
        )
    elif origin_type is set:
        (set_type,) = typing.get_args(typ)  # unpack single tuple element
        return set(json_to_object(set_type, item) for item in data)
    elif origin_type is tuple:
        return tuple(
            json_to_object(member_type, item)
            for (member_type, item) in zip(
                (member_type for member_type in typing.get_args(typ)),
                (item for item in data),
            )
        )
    elif origin_type is Union:
        for t in typing.get_args(typ):
            # iterate over potential types of discriminated union
            try:
                return json_to_object(t, data)
            except KeyError:
                # indicates a required field is missing from JSON dict,
                # i.e. we don't have the type that we are looking for
                continue

        raise KeyError(f"type `{typ}` could not be instantiated from: {data}")

    if not inspect.isclass(typ):
        raise TypeError(f"unable to de-serialize unrecognized type `{typ}`")

    if is_named_tuple_type(typ):
        object_dict = {
            field_name: json_to_object(field_type, data[field_name])
            for field_name, field_type in typing.get_type_hints(typ).items()
        }
        return typ(**object_dict)

    if issubclass(typ, enum.Enum):
        return typ(data)

    # check if object has custom serialization method
    convert_func = getattr(typ, "from_json", None)
    if callable(convert_func):
        return convert_func(data)

    obj = object.__new__(typ)
    for property_name, property_type in get_class_properties(typ):
        json_name = python_id_to_json_field(property_name)
        if is_type_optional(property_type):
            if json_name in data:
                setattr(
                    obj,
                    property_name,
                    json_to_object(
                        unwrap_optional_type(property_type), data[json_name]
                    ),
                )
        else:
            setattr(
                obj,
                property_name,
                json_to_object(property_type, data[json_name]),
            )
    return obj


def json_dump_string(json_object: JsonType) -> str:
    "Dump an object as a JSON string with a compact representation."

    return json.dumps(
        json_object, ensure_ascii=False, check_circular=False, separators=(",", ":")
    )


def is_type_enum(typ: Type) -> bool:
    "True if the specified type is an enumeration type."

    # use an explicit isinstance(..., type) check to filter out special forms like generics
    return isinstance(typ, type) and issubclass(typ, enum.Enum)


def is_type_optional(typ: Type) -> bool:
    "True if the type annotation corresponds to an optional type (e.g. Optional[T] or Union[T1,T2,None])."

    if typing.get_origin(typ) is Union:  # Optional[T] is represented as Union[T, None]
        return type(None) in typing.get_args(typ)

    return False


def unwrap_optional_type(typ: Type[Optional[T]]) -> Type[T]:
    "Extracts the type qualified as optional (e.g. returns T for Optional[T])."

    # Optional[T] is represented internally as Union[T, None]
    if typing.get_origin(typ) is not Union:
        raise TypeError("optional type must have un-subscripted type of Union")

    # will automatically unwrap Union[T] into T
    return Union[
        tuple(filter(lambda item: item is not type(None), typing.get_args(typ)))  # type: ignore
    ]


def is_generic_list(typ: Type) -> bool:
    "True if the specified type is a generic list, i.e. `List[T]`."

    return typing.get_origin(typ) is list


def unwrap_generic_list(typ: Type[List[T]]) -> Type[T]:
    (list_type,) = typing.get_args(typ)  # unpack single tuple element
    return list_type


def is_generic_dict(typ: Type) -> bool:
    "True if the specified type is a generic dictionary, i.e. `Dict[KeyType, ValueType]`."

    return typing.get_origin(typ) is dict


def unwrap_generic_dict(typ: Type[Dict[K, V]]) -> Tuple[Type[K], Type[V]]:
    key_type, value_type = typing.get_args(typ)
    return key_type, value_type


try:
    import docstring_parser

    def get_class_docstrings(typ: Type) -> Tuple[Optional[str], Optional[str]]:
        docstring: docstring_parser.Docstring = docstring_parser.parse(typ.__doc__)
        return docstring.short_description, docstring.long_description

    def get_class_property_docstrings(typ: Type) -> Dict[str, str]:
        docstring: docstring_parser.Docstring = docstring_parser.parse(typ.__doc__)
        return {param.arg_name: param.description for param in docstring.params}


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


@dataclasses.dataclass
class SchemaOptions:
    definitions_path: str = "#/definitions/"
    use_descriptions: bool = True


class JsonSchemaGenerator:
    """Creates a JSON schema with user-defined type definitions."""

    type_catalog: ClassVar[Dict[Type, Schema]] = {}
    types_used: Dict[str, Type]
    options: SchemaOptions

    def __init__(self, options: SchemaOptions = None):
        if options is None:
            self.options = SchemaOptions
        else:
            self.options = options
        self.types_used = {}

    def type_to_schema(self, typ: Type, force_expand: bool = False) -> Schema:
        if isinstance(typ, str):
            raise TypeError(f"object is not a type but a string")

        if typ is None:
            return {"type": "null"}
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
        elif typ is uuid.UUID:
            # f81d4fae-7dec-11d0-a765-00a0c91e6bf6
            return {"type": "string", "format": "uuid"}

        if isinstance(typ, typing.ForwardRef):
            fwd: typing.ForwardRef = typ
            identifier = fwd.__forward_arg__
            typ = eval(identifier)
            self.types_used[identifier] = typ
            return {"$ref": f"{self.options.definitions_path}{identifier}"}

        if is_type_enum(typ):
            enum_values = [e.value for e in typ]
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

        if not force_expand and typ in __class__.type_catalog:
            # user-defined type
            identifier = typ.__name__
            self.types_used[identifier] = typ
            return {"$ref": f"{self.options.definitions_path}{identifier}"}
        else:
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

    def _subtype_to_schema(self, subtype: Type) -> Schema:
        subschema = __class__.type_catalog[subtype]
        if subschema is not None:
            type_schema = subschema.copy()

            # add descriptive text (if present)
            if self.options.use_descriptions:
                type_schema.update(docstring_to_schema(subtype))
        else:
            type_schema = self.type_to_schema(subtype, force_expand=True)

        return type_schema

    def classdef_to_schema(self, typ: Type) -> Tuple[Schema, Dict[str, Schema]]:
        self.types_used = {}
        try:
            type_schema = self.type_to_schema(typ)

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
                    types_defined[sub_name] = self._subtype_to_schema(sub_type)

            type_definitions = dict(sorted(types_defined.items()))
        finally:
            self.types_used = {}

        return type_schema, type_definitions


def classdef_to_schema(typ: Type, options: SchemaOptions = None) -> Schema:
    """Returns the JSON schema corresponding to the given type.

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
    """Validates if the JSON dictionary object conforms to the expected type.

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


def register_schema(cls, schema=None):
    JsonSchemaGenerator.type_catalog[cls] = schema
    return cls


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


register_schema(JsonType)
