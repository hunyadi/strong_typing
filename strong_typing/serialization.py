import base64
import dataclasses
import datetime
import enum
import inspect
import json
import keyword
import re
import typing
import uuid
from typing import Any, Type, TypeVar, Union

from .auxiliary import Alias
from .core import JsonType
from .inspection import (
    get_annotation,
    get_class_properties,
    is_dataclass_instance,
    is_named_tuple_instance,
    is_named_tuple_type,
    is_type_optional,
    unwrap_optional_type,
)

T = TypeVar("T")


def python_id_to_json_field(python_id: str, python_type: type = None) -> str:
    """
    Convert a Python identifier to a JSON field name.

    Authors may use an underscore appended at the end of a Python identifier as per PEP 8 if it clashes with a Python
    keyword: e.g. `in` would become `in_` and `from` would become `from_`. Remove these suffixes when exporting to JSON.

    Authors may supply an explicit alias with the type annotation `Alias`, e.g. `Annotated[MyType, Alias("alias")]`.
    """

    if python_type is not None:
        alias = get_annotation(python_type, Alias)
        if alias:
            return alias.name

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

    :raises KeyError: Deserialization for a class or union type has failed because a matching member was not found.
    :raises TypeError: Deserialization for data has failed due to a type mismatch.
    """

    # check for well-known types
    if obj is None:
        # can be directly represented in JSON
        return None
    elif isinstance(obj, (bool, int, float, str)):
        # can be directly represented in JSON
        return obj
    elif isinstance(obj, bytes):
        return base64.b64encode(obj).decode("ascii")
    elif isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        fmt = obj.isoformat()
        if fmt.endswith("+00:00"):
            fmt = f"{fmt[:-6]}Z"  # Python's isoformat() does not support military time zones like "Zulu" for UTC
        return fmt
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
            object_dict[
                python_id_to_json_field(field.name, field.type)
            ] = object_to_json(value)
        return object_dict

    elif is_named_tuple_instance(obj):
        object_dict = {}
        for field in type(obj)._fields:
            value = getattr(obj, field)  # type: ignore
            if value is None:
                continue
            object_dict[python_id_to_json_field(field)] = object_to_json(value)  # type: ignore
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


@typing.no_type_check
def json_to_object(typ: Type[T], data: JsonType) -> T:
    """
    Create an object from a representation that has been de-serialized from JSON.
    Fundamental types (e.g. numeric types) are left as is. Objects with properties are populated
    from dictionaries of key-value pairs using reflection (enumerating instance type annotations).
    """

    # check for well-known types
    if typ is type(None):
        if data is not None:
            raise TypeError(
                f"`None` type expects JSON `null` but instead received: {data}"
            )
        return None
    elif typ is bool:
        if not isinstance(data, bool):
            raise TypeError(
                f"`bool` type expects JSON `boolean` data but instead received: {data}"
            )
        return bool(data)
    elif typ is int:
        if not isinstance(data, int):
            raise TypeError(
                f"`int` type expects integer data as JSON `number` but instead received: {data}"
            )
        return int(data)
    elif typ is float:
        if not isinstance(data, float) and not isinstance(data, int):
            raise TypeError(
                f"`int` type expects data as JSON `number` but instead received: {data}"
            )
        return float(data)
    elif typ is str:
        if not isinstance(data, str):
            raise TypeError(
                f"`str` type expects JSON `string` data but instead received: {data}"
            )
        return str(data)
    elif typ is bytes:
        return base64.b64decode(data)
    elif typ is datetime.datetime or typ is datetime.date or typ is datetime.time:
        if not isinstance(data, str):
            raise TypeError(
                f"`{typ.__name__}` type expects JSON `string` data but instead received: {data}"
            )

        if (typ is datetime.datetime or typ is datetime.time) and data.endswith("Z"):
            data = f"{data[:-1]}+00:00"  # Python's isoformat() does not support military time zones like "Zulu" for UTC

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
            except (KeyError, TypeError):
                # indicates a required field is missing from JSON dict -OR- the data cannot be cast to the expected type,
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
        json_name = python_id_to_json_field(property_name, property_type)
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
