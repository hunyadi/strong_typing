import abc
import base64
import datetime
import enum
import functools
import inspect
import json
import types
import typing
import uuid
from typing import (
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from .core import JsonType
from .deserializer import create_deserializer
from .exception import JsonTypeError, JsonValueError
from .inspection import (
    enum_value_types,
    get_class_properties,
    get_resolved_hints,
    is_dataclass_type,
    is_named_tuple_type,
    is_reserved_property,
    is_type_annotated,
    unwrap_annotated_type,
)
from .mapping import python_field_to_json_property

T = TypeVar("T")


class Serializer(abc.ABC):
    @abc.abstractmethod
    def generate(self, data: Any) -> JsonType:
        ...


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


class UntypedListSerializer(Serializer):
    def generate(self, obj: list) -> JsonType:
        return [object_to_json(item) for item in obj]


class UntypedDictSerializer(Serializer):
    def generate(self, obj: dict) -> JsonType:
        if obj and isinstance(next(iter(obj.keys())), enum.Enum):
            iterator = (
                (key.value, object_to_json(value)) for key, value in obj.items()
            )
        else:
            iterator = ((str(key), object_to_json(value)) for key, value in obj.items())
        return dict(iterator)


class UntypedSetSerializer(Serializer):
    def generate(self, obj: set) -> JsonType:
        return [object_to_json(item) for item in obj]


class UntypedTupleSerializer(Serializer):
    def generate(self, obj: tuple) -> JsonType:
        return [object_to_json(item) for item in obj]


class TypedCollectionSerializer(Serializer):
    generator: Serializer

    def __init__(self, item_type: type) -> None:
        self.generator = create_serializer(item_type)


class TypedListSerializer(TypedCollectionSerializer):
    def generate(self, obj: list) -> JsonType:
        return [self.generator.generate(item) for item in obj]


class TypedStringDictSerializer(TypedCollectionSerializer):
    def __init__(self, value_type: type) -> None:
        super().__init__(value_type)

    def generate(self, obj: dict) -> JsonType:
        return {key: self.generator.generate(value) for key, value in obj.items()}


class TypedEnumDictSerializer(TypedCollectionSerializer):
    def __init__(self, key_type: Type[enum.Enum], value_type: type) -> None:
        super().__init__(value_type)

        value_types = enum_value_types(key_type)
        if len(value_types) != 1:
            raise JsonTypeError(
                f"invalid key type, enumerations must have a consistent member value type but several types found: {value_types}"
            )

        value_type = value_types.pop()
        if value_type is not str:
            raise JsonTypeError(
                "invalid enumeration key type, expected `enum.Enum` with string values"
            )

    def generate(self, obj: dict) -> JsonType:
        return {key.value: self.generator.generate(value) for key, value in obj.items()}


class TypedSetSerializer(TypedCollectionSerializer):
    def generate(self, obj: set) -> JsonType:
        return [self.generator.generate(item) for item in obj]


class TypedTupleSerializer(Serializer):
    item_generators: Tuple[Serializer, ...]

    def __init__(self, item_types: Tuple[type, ...]) -> None:
        self.item_generators = tuple(
            create_serializer(item_type) for item_type in item_types
        )

    def generate(self, obj: set) -> JsonType:
        return [
            item_generator.generate(item)
            for item_generator, item in zip(self.item_generators, obj)
        ]


class CustomSerializer(Serializer):
    converter: Callable[[object], JsonType]

    def __init__(self, converter: Callable[[object], JsonType]) -> None:
        self.converter = converter  # type: ignore

    def generate(self, obj: object) -> JsonType:
        return self.converter(obj)  # type: ignore


class FieldSerializer:
    """
    Serializes a Python object field into a JSON property.

    :param field_name: The name of the field in a Python class to read data from.
    :param property_name: The name of the JSON property to write to a JSON `object`.
    :param generator: A compatible serializer that can handle the field's type.
    """

    field_name: str
    property_name: str
    generator: Serializer

    def __init__(
        self, field_name: str, property_name: str, generator: Serializer
    ) -> None:
        self.field_name = field_name
        self.property_name = property_name
        self.generator = generator

    def generate_field(self, obj: object, object_dict: Dict[str, JsonType]) -> None:
        value = getattr(obj, self.field_name)
        if value is not None:
            object_dict[self.property_name] = self.generator.generate(value)


class TypedClassSerializer(Serializer):
    property_generators: List[FieldSerializer]

    def __init__(self, class_type: type) -> None:
        self.property_generators = [
            FieldSerializer(
                field_name,
                python_field_to_json_property(field_name, field_type),
                create_serializer(field_type),
            )
            for field_name, field_type in get_class_properties(class_type)
        ]

    def generate(self, obj: object) -> JsonType:
        object_dict: Dict[str, JsonType] = {}
        for property_generator in self.property_generators:
            property_generator.generate_field(obj, object_dict)

        return object_dict


class TypedNamedTupleSerializer(TypedClassSerializer):
    def __init__(self, class_type: Type[NamedTuple]) -> None:
        super().__init__(class_type)


class DataclassSerializer(TypedClassSerializer):
    def __init__(self, class_type: type) -> None:
        super().__init__(class_type)


class UnionSerializer(Serializer):
    def generate(self, obj: Any) -> JsonType:
        return object_to_json(obj)


class UntypedNamedTupleSerializer(Serializer):
    fields: Dict[str, str]

    def __init__(self, class_type: Type[NamedTuple]) -> None:
        # named tuples are also instances of tuple
        self.fields = {}
        field_names: Tuple[str, ...] = class_type._fields
        for field_name in field_names:
            self.fields[field_name] = python_field_to_json_property(field_name)

    def generate(self, obj: object) -> JsonType:
        object_dict = {}
        for field_name, property_name in self.fields.items():
            value = getattr(obj, field_name)
            object_dict[property_name] = object_to_json(value)

        return object_dict


class UntypedClassSerializer(Serializer):
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


def create_serializer(typ: type) -> Serializer:
    if isinstance(typ, type):
        return _fetch_serializer(typ)
    else:
        # special forms are not always hashable
        return _create_serializer(typ)


@functools.lru_cache(maxsize=None)
def _fetch_serializer(typ: type) -> Serializer:
    return _create_serializer(typ)


def _create_serializer(typ: type) -> Serializer:
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

    # dynamically-typed collection types
    if typ is list:
        return UntypedListSerializer()
    elif typ is dict:
        return UntypedDictSerializer()
    elif typ is set:
        return UntypedSetSerializer()
    elif typ is tuple:
        return UntypedTupleSerializer()

    # generic types (e.g. list, dict, set, etc.)
    origin_type = typing.get_origin(typ)
    if origin_type is list:
        (list_item_type,) = typing.get_args(typ)  # unpack single tuple element
        return TypedListSerializer(list_item_type)
    elif origin_type is dict:
        key_type, value_type = typing.get_args(typ)
        if key_type is str:
            return TypedStringDictSerializer(value_type)
        elif issubclass(key_type, enum.Enum):
            return TypedEnumDictSerializer(key_type, value_type)
    elif origin_type is set:
        (set_member_type,) = typing.get_args(typ)  # unpack single tuple element
        return TypedSetSerializer(set_member_type)
    elif origin_type is tuple:
        return TypedTupleSerializer(typing.get_args(typ))
    elif origin_type is Union:
        return UnionSerializer()

    if is_type_annotated(typ):
        return create_serializer(unwrap_annotated_type(typ))

    # check if object has custom serialization method
    convert_func = getattr(typ, "to_json", None)
    if callable(convert_func):
        return CustomSerializer(convert_func)

    if issubclass(typ, enum.Enum):
        return EnumSerializer()
    if is_dataclass_type(typ):
        return DataclassSerializer(typ)
    if is_named_tuple_type(typ):
        if typ.__annotations__:
            return TypedNamedTupleSerializer(typ)
        else:
            return UntypedNamedTupleSerializer(typ)

    # fail early if caller passes an object with an exotic type
    if (
        typ is types.FunctionType
        or typ is types.ModuleType
        or typ is type
        or typ is types.MethodType
    ):
        raise TypeError(f"object of type {typ} cannot be represented in JSON")

    if get_resolved_hints(typ):
        return TypedClassSerializer(typ)
    else:
        return UntypedClassSerializer()


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
