import base64
import dataclasses
import datetime
import enum
import functools
import inspect
import json
import types
import uuid
from typing import Any, Callable, Dict, NamedTuple, TextIO, Tuple, Type, TypeVar, Union

from .core import JsonType
from .deserializer import create_deserializer
from .exception import JsonValueError
from .inspection import is_dataclass_type, is_named_tuple_type, is_reserved_property
from .mapping import python_field_to_json_property

T = TypeVar("T")


class Serializer:
    def generate(self, data: Any) -> JsonType:
        pass


class NoneSerializer(Serializer):
    def generate(self, data: None) -> None:
        # can be directly represented in JSON
        return None


class BoolSerializer(Serializer):
    def generate(self, data: bool) -> bool:
        # can be directly represented in JSON
        return data


class IntSerializer(Serializer):
    def generate(self, data: int) -> int:
        # can be directly represented in JSON
        return data


class FloatSerializer(Serializer):
    def generate(self, data: float) -> float:
        # can be directly represented in JSON
        return data


class StringSerializer(Serializer):
    def generate(self, data: str) -> str:
        # can be directly represented in JSON
        return data


class BytesSerializer(Serializer):
    def generate(self, data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")


class DateTimeSerializer(Serializer):
    def generate(self, obj: datetime.datetime) -> str:
        if obj.tzinfo is None:
            raise JsonValueError(
                f"timestamp lacks explicit time zone designator: {obj}"
            )
        fmt = obj.isoformat()
        if fmt.endswith("+00:00"):
            fmt = f"{fmt[:-6]}Z"  # Python's isoformat() does not support military time zones like "Zulu" for UTC
        return fmt


class DateSerializer(Serializer):
    def generate(self, obj: datetime.date) -> str:
        return obj.isoformat()


class TimeSerializer(Serializer):
    def generate(self, obj: datetime.time) -> str:
        return obj.isoformat()


class UUIDSerializer(Serializer):
    def generate(self, obj: uuid.UUID) -> str:
        return str(obj)


class EnumSerializer(Serializer):
    def generate(self, obj: enum.Enum) -> Union[int, str]:
        return obj.value


class ListSerializer(Serializer):
    def generate(self, obj: list) -> JsonType:
        return [object_to_json(item) for item in obj]


class DictSerializer(Serializer):
    def generate(self, obj: dict) -> JsonType:
        if obj and isinstance(next(iter(obj.keys())), enum.Enum):
            iterator = (
                (key.value, object_to_json(value)) for key, value in obj.items()
            )
        else:
            iterator = ((str(key), object_to_json(value)) for key, value in obj.items())
        return dict(iterator)


class SetSerializer(Serializer):
    def generate(self, obj: set) -> JsonType:
        return [object_to_json(item) for item in obj]


class TupleSerializer(Serializer):
    def generate(self, obj: tuple) -> JsonType:
        return [object_to_json(item) for item in obj]


class CustomSerializer(Serializer):
    converter: Callable[[object], JsonType]

    def __init__(self, converter: Callable[[object], JsonType]) -> None:
        self.converter = converter  # type: ignore

    def generate(self, obj: object) -> JsonType:
        return self.converter(obj)  # type: ignore


class ClassSerializer(Serializer):
    fields: Dict[str, str]

    def generate(self, obj: object) -> JsonType:
        object_dict = {}
        for field_name, property_name in self.fields.items():
            value = getattr(obj, field_name)
            if value is None:
                continue
            object_dict[property_name] = object_to_json(value)
        return object_dict


class NamedTupleSerializer(ClassSerializer):
    def __init__(self, class_type: Type[NamedTuple]) -> None:
        # named tuples are also instances of tuple
        self.fields = {}
        field_names: Tuple[str, ...] = class_type._fields
        for field_name in field_names:
            self.fields[field_name] = python_field_to_json_property(field_name)


class DataclassSerializer(ClassSerializer):
    def __init__(self, class_type: type) -> None:
        self.fields = {}
        for field in dataclasses.fields(class_type):
            self.fields[field.name] = python_field_to_json_property(
                field.name, field.type
            )


class DynamicClassSerializer(Serializer):
    def __init__(self, class_type: type) -> None:
        pass

    def generate(self, obj: object) -> JsonType:
        # iterate over object attributes to get a standard representation
        object_dict = {}
        for name in dir(obj):
            if is_reserved_property(name):
                continue

            value = getattr(obj, name)
            if value is None:
                continue

            # filter instance methods
            if inspect.ismethod(value):
                continue

            object_dict[python_field_to_json_property(name)] = object_to_json(value)

        return object_dict


@functools.lru_cache(maxsize=None)
def create_serializer(typ: type) -> Serializer:
    # check for well-known types
    if typ is type(None):
        return NoneSerializer()
    elif typ is bool:
        return BoolSerializer()
    elif typ is int:
        return IntSerializer()
    elif typ is float:
        return FloatSerializer()
    elif typ is str:
        return StringSerializer()
    elif typ is bytes:
        return BytesSerializer()
    elif typ is datetime.datetime:
        return DateTimeSerializer()
    elif typ is datetime.date:
        return DateSerializer()
    elif typ is datetime.time:
        return TimeSerializer()
    elif typ is uuid.UUID:
        return UUIDSerializer()

    # check for container types
    if typ is list:
        return ListSerializer()
    elif typ is dict:
        return DictSerializer()
    elif typ is set:
        return SetSerializer()
    elif typ is tuple:
        return TupleSerializer()

    # check if object has custom serialization method
    convert_func = getattr(typ, "to_json", None)
    if callable(convert_func):
        return CustomSerializer(convert_func)

    if issubclass(typ, enum.Enum):
        return EnumSerializer()
    if is_dataclass_type(typ):
        return DataclassSerializer(typ)
    if is_named_tuple_type(typ):
        return NamedTupleSerializer(typ)

    # fail early if caller passes an object with an exotic type
    if (
        typ is types.FunctionType
        or typ is types.ModuleType
        or typ is type
        or typ is types.MethodType
    ):
        raise TypeError(f"object of type {typ} cannot be represented in JSON")

    return DynamicClassSerializer(typ)


def object_to_json(obj: Any) -> JsonType:
    """
    Converts a Python object to a representation that can be exported to JSON.

    * Fundamental types (e.g. numeric types) are written as is.
    * Date and time types are serialized in the ISO 8601 format with time zone.
    * A byte array is written as a string with Base64 encoding.
    * UUIDs are written as a UUID string.
    * Enumerations are written as their value.
    * Containers (e.g. `list`, `dict`, `set`, `tuple`) are exported recursively.
    * Objects with properties (including data class types) are converted to a dictionaries of key-value pairs.
    """

    typ: type = type(obj)
    generator = create_serializer(typ)
    return generator.generate(obj)


def json_to_object(typ: Type[T], data: JsonType) -> T:
    """
    Creates an object from a representation that has been de-serialized from JSON.

    When de-serializing a JSON object into a Python object, the following transformations are applied:

    * Fundamental types are parsed as `bool`, `int`, `float` or `str`.
    * Date and time types are parsed from the ISO 8601 format with time zone into the corresponding Python type
      `datetime`, `date` or `time`
    * A byte array is read from a string with Base64 encoding into a `bytes` instance.
    * UUIDs are extracted from a UUID string into a `uuid.UUID` instance.
    * Enumerations are instantiated with a lookup on enumeration value.
    * Containers (e.g. `list`, `dict`, `set`, `tuple`) are parsed recursively.
    * Complex objects with properties (including data class types) are populated from dictionaries of key-value pairs
      using reflection (enumerating type annotations).

    :raises TypeError: A de-serializing engine cannot be constructed for the input type.
    :raises JsonKeyError: Deserialization for a class or union type has failed because a matching member was not found.
    :raises JsonTypeError: Deserialization for data has failed due to a type mismatch.
    """

    parser = create_deserializer(typ)
    return parser.parse(data)


def json_dump_string(json_object: JsonType) -> str:
    "Dump an object as a JSON string with a compact representation."

    return json.dumps(
        json_object, ensure_ascii=False, check_circular=False, separators=(",", ":")
    )


def json_dump(json_object: JsonType, file: TextIO) -> None:
    json.dump(
        json_object,
        file,
        ensure_ascii=False,
        check_circular=False,
        separators=(",", ":"),
    )
    file.write("\n")
