import abc
import base64
import dataclasses
import datetime
import enum
import functools
import inspect
import typing
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from .core import JsonType
from .exception import JsonKeyError, JsonTypeError, JsonValueError
from .inspection import (
    create_object,
    enum_value_types,
    get_class_properties,
    get_resolved_hints,
    is_dataclass_instance,
    is_dataclass_type,
    is_named_tuple_type,
    is_type_annotated,
    is_type_optional,
    unwrap_annotated_type,
    unwrap_optional_type,
)
from .mapping import python_field_to_json_property
from .name import python_type_to_str


class Deserializer(abc.ABC):
    "Parses a JSON value into a Python type."

    @abc.abstractmethod
    def parse(self, data: JsonType) -> Any:
        ...


class NoneDeserializer(Deserializer):
    "Parses JSON `null` values into Python `None`."

    def parse(self, data: JsonType) -> None:
        if data is not None:
            raise JsonTypeError(
                f"`None` type expects JSON `null` but instead received: {data}"
            )
        return None


class BoolDeserializer(Deserializer):
    "Parses JSON `boolean` values into Python `bool` type."

    def parse(self, data: JsonType) -> bool:
        if not isinstance(data, bool):
            raise JsonTypeError(
                f"`bool` type expects JSON `boolean` data but instead received: {data}"
            )
        return bool(data)


class IntDeserializer(Deserializer):
    "Parses JSON `number` values into Python `int` type."

    def parse(self, data: JsonType) -> int:
        if not isinstance(data, int):
            raise JsonTypeError(
                f"`int` type expects integer data as JSON `number` but instead received: {data}"
            )
        return int(data)


class FloatDeserializer(Deserializer):
    "Parses JSON `number` values into Python `float` type."

    def parse(self, data: JsonType) -> float:
        if not isinstance(data, float) and not isinstance(data, int):
            raise JsonTypeError(
                f"`int` type expects data as JSON `number` but instead received: {data}"
            )
        return float(data)


class StringDeserializer(Deserializer):
    "Parses JSON `string` values into Python `str` type."

    def parse(self, data: JsonType) -> str:
        if not isinstance(data, str):
            raise JsonTypeError(
                f"`str` type expects JSON `string` data but instead received: {data}"
            )
        return str(data)


class BytesDeserializer(Deserializer):
    "Parses JSON `string` values of Base64-encoded strings into Python `bytes` type."

    def parse(self, data: JsonType) -> bytes:
        if not isinstance(data, str):
            raise JsonTypeError(
                f"`bytes` type expects JSON `string` data but instead received: {data}"
            )
        return base64.b64decode(data, validate=True)


class DateTimeDeserializer(Deserializer):
    "Parses JSON `string` values representing timestamps in ISO 8601 format to Python `datetime` with time zone."

    def parse(self, data: JsonType) -> datetime.datetime:
        if not isinstance(data, str):
            raise JsonTypeError(
                f"`datetime` type expects JSON `string` data but instead received: {data}"
            )

        if data.endswith("Z"):
            data = f"{data[:-1]}+00:00"  # Python's isoformat() does not support military time zones like "Zulu" for UTC
        timestamp = datetime.datetime.fromisoformat(data)
        if timestamp.tzinfo is None:
            raise JsonValueError(
                f"timestamp lacks explicit time zone designator: {data}"
            )
        return timestamp


class DateDeserializer(Deserializer):
    "Parses JSON `string` values representing dates in ISO 8601 format to Python `date` type."

    def parse(self, data: JsonType) -> datetime.date:
        if not isinstance(data, str):
            raise JsonTypeError(
                f"`date` type expects JSON `string` data but instead received: {data}"
            )

        return datetime.date.fromisoformat(data)


class TimeDeserializer(Deserializer):
    "Parses JSON `string` values representing time instances in ISO 8601 format to Python `time` type with time zone."

    def parse(self, data: JsonType) -> datetime.time:
        if not isinstance(data, str):
            raise JsonTypeError(
                f"`time` type expects JSON `string` data but instead received: {data}"
            )

        return datetime.time.fromisoformat(data)


class UUIDDeserializer(Deserializer):
    "Parses JSON `string` values of UUID strings into Python `uuid.UUID` type."

    def parse(self, data: JsonType) -> uuid.UUID:
        if not isinstance(data, str):
            raise JsonTypeError(
                f"`UUID` type expects JSON `string` data but instead received: {data}"
            )
        return uuid.UUID(data)


class ListDeserializer(Deserializer):
    "Recursively de-serializes a JSON array into a Python `list`."

    item_type: type
    item_parser: Deserializer

    def __init__(self, item_type: type) -> None:
        self.item_type = item_type
        self.item_parser = create_deserializer(item_type)

    def parse(self, data: JsonType) -> list:
        if not isinstance(data, list):
            type_name = python_type_to_str(self.item_type)
            raise JsonTypeError(
                f"type `List[{type_name}]` expects JSON `array` data but instead received: {data}"
            )

        return [self.item_parser.parse(item) for item in data]


class DictDeserializer(Deserializer):
    "Recursively de-serializes a JSON object into a Python `dict`."

    key_type: type
    value_type: type
    value_parser: Deserializer

    def __init__(self, key_type: type, value_type: type) -> None:
        self.key_type = key_type
        self.value_type = value_type
        self._check_key_type()
        self.value_parser = create_deserializer(value_type)

    def _check_key_type(self) -> None:
        if self.key_type is str:
            return

        if issubclass(self.key_type, enum.Enum):
            value_types = enum_value_types(self.key_type)
            if len(value_types) != 1:
                raise JsonTypeError(
                    f"type `{self.container_type}` has invalid key type, enumerations must have a consistent member value type but several types found: {value_types}"
                )
            value_type = value_types.pop()
            if value_type is not str:
                f"`type `{self.container_type}` has invalid enumeration key type, expected `enum.Enum` with string values"
            return

        raise JsonTypeError(
            f"`type `{self.container_type}` has invalid key type, expected `str` or `enum.Enum` with string values"
        )

    @property
    def container_type(self) -> str:
        key_type_name = python_type_to_str(self.key_type)
        value_type_name = python_type_to_str(self.value_type)
        return f"Dict[{key_type_name}, {value_type_name}]"

    def parse(self, data: JsonType) -> dict:
        if not isinstance(data, dict):
            raise JsonTypeError(
                f"`type `{self.container_type}` expects JSON `object` data but instead received: {data}"
            )

        return dict(
            (self.key_type(key), self.value_parser.parse(value))
            for key, value in data.items()
        )


class SetDeserializer(Deserializer):
    "Recursively de-serializes a JSON list into a Python `set`."

    member_type: type
    member_parser: Deserializer

    def __init__(self, member_type: type) -> None:
        self.member_type = member_type
        self.member_parser = create_deserializer(member_type)

    def parse(self, data: JsonType) -> set:
        if not isinstance(data, list):
            type_name = python_type_to_str(self.member_type)
            raise JsonTypeError(
                f"type `Set[{type_name}]` expects JSON `array` data but instead received: {data}"
            )

        return set(self.member_parser.parse(item) for item in data)


class TupleDeserializer(Deserializer):
    "Recursively de-serializes a JSON list into a Python `tuple`."

    item_types: Tuple[type, ...]
    item_parsers: Tuple[Deserializer, ...]

    def __init__(self, item_types: Tuple[type, ...]) -> None:
        self.item_types = item_types
        self.item_parsers = tuple(
            create_deserializer(item_type) for item_type in item_types
        )

    @property
    def container_type(self) -> str:
        type_names = ", ".join(
            python_type_to_str(item_type) for item_type in self.item_types
        )
        return f"Tuple[{type_names}]"

    def parse(self, data: JsonType) -> tuple:
        if not isinstance(data, list) or len(data) != len(self.item_parsers):
            if not isinstance(data, list):
                raise JsonTypeError(
                    f"type `{self.container_type}` expects JSON `array` data but instead received: {data}"
                )
            else:
                raise JsonValueError(
                    f"type `{self.container_type}` expects a JSON `array` of length {len(self.item_parsers)} but received length {len(data)}"
                )

        return tuple(
            item_parser.parse(item)
            for item_parser, item in zip(self.item_parsers, data)
        )


class UnionDeserializer(Deserializer):
    "De-serializes a JSON value (of any type) into a Python union type."

    member_types: Tuple[type, ...]
    member_parsers: Tuple[Deserializer, ...]

    def __init__(self, member_types: Tuple[type, ...]) -> None:
        self.member_types = member_types
        self.member_parsers = tuple(
            create_deserializer(member_type) for member_type in member_types
        )

    def parse(self, data: JsonType) -> Any:
        for member_parser in self.member_parsers:
            # iterate over potential types of discriminated union
            try:
                return member_parser.parse(data)
            except (JsonKeyError, JsonTypeError) as k:
                # indicates a required field is missing from JSON dict -OR- the data cannot be cast to the expected type,
                # i.e. we don't have the type that we are looking for
                continue

        type_names = ", ".join(
            python_type_to_str(member_type) for member_type in self.member_types
        )
        raise JsonKeyError(
            f"type `Union[{type_names}]` could not be instantiated from: {data}"
        )


class EnumDeserializer(Deserializer):
    "Returns an enumeration instance based on the enumeration value read from a JSON value."

    enum_type: Type[enum.Enum]

    def __init__(self, enum_type: type) -> None:
        self.enum_type = enum_type

    def parse(self, data: JsonType) -> enum.Enum:
        return self.enum_type(data)


class CustomDeserializer(Deserializer):
    "Uses the `from_json` class method in class to de-serialize the object from JSON."

    converter: Callable[[JsonType], Any]

    def __init__(self, converter: Callable[[JsonType], Any]) -> None:
        self.converter = converter  # type: ignore

    def parse(self, data: JsonType) -> Any:
        return self.converter(data)  # type: ignore


class DeferredDeserializer(Deserializer):
    """
    Dynamically instantiates a deserializer to parse a JSON value.

    Required for de-serializing recursively defined types (e.g. tree structures).
    """

    evaluated_type: type

    def __init__(self, evaluated_type: type) -> None:
        self.evaluated_type = evaluated_type

    def parse(self, data: JsonType) -> Any:
        deserializer = create_deserializer(self.evaluated_type)
        return deserializer.parse(data)


class FieldDeserializer(abc.ABC):
    """
    Deserializes a JSON property into a Python object field.

    :param property_name: The name of the JSON property to read from a JSON `object`.
    :param field_name: The name of the field in a Python class to write data to.
    :param parser: A compatible deserializer that can handle the field's type.
    """

    property_name: str
    field_name: str
    parser: Deserializer

    def __init__(
        self, property_name: str, field_name: str, parser: Deserializer
    ) -> None:
        self.property_name = property_name
        self.field_name = field_name
        self.parser = parser

    @abc.abstractmethod
    def parse_field(self, data: Dict[str, JsonType]) -> Any:
        ...


class RequiredFieldDeserializer(FieldDeserializer):
    "Deserializes a JSON property into a mandatory Python object field."

    def parse_field(self, data: Dict[str, JsonType]) -> Any:
        if self.property_name not in data:
            raise JsonKeyError(
                f"missing required property `{self.property_name}` from JSON object: {data}"
            )

        return self.parser.parse(data[self.property_name])


class OptionalFieldDeserializer(FieldDeserializer):
    "Deserializes a JSON property into an optional Python object field with a default value of `None`."

    def parse_field(self, data: Dict[str, JsonType]) -> Any:
        value = data.get(self.property_name)
        if value is not None:
            return self.parser.parse(value)
        else:
            return None


class DefaultFieldDeserializer(FieldDeserializer):
    "Deserializes a JSON property into an optional Python object field with an explicit default value."

    default_value: Optional[Any] = None

    def __init__(
        self,
        property_name: str,
        field_name: str,
        parser: Deserializer,
        default_value: Optional[Any],
    ) -> None:
        super().__init__(property_name, field_name, parser)
        self.default_value = default_value

    def parse_field(self, data: Dict[str, JsonType]) -> Any:
        value = data.get(self.property_name)
        if value is not None:
            return self.parser.parse(value)
        else:
            return self.default_value


class DefaultFactoryFieldDeserializer(FieldDeserializer):
    "Deserializes a JSON property into an optional Python object field with an explicit default value factory."

    default_factory: Callable[[], Any]

    def __init__(
        self,
        property_name: str,
        field_name: str,
        parser: Deserializer,
        default_factory: Callable[[], Any],
    ) -> None:
        super().__init__(property_name, field_name, parser)
        self.default_factory = default_factory  # type: ignore

    def parse_field(self, data: Dict[str, JsonType]) -> Any:
        value = data.get(self.property_name)
        if value is not None:
            return self.parser.parse(value)
        else:
            return self.default_factory()  # type: ignore


class ClassDeserializer(Deserializer):
    "Base class for de-serializing class-like types such as data classes, named tuples and regular classes."

    class_type: type
    property_parsers: List[FieldDeserializer]

    def __init__(self, class_type: type) -> None:
        self.class_type = class_type

    def parse(self, data: JsonType) -> object:
        if not isinstance(data, dict):
            type_name = python_type_to_str(self.class_type)
            raise JsonTypeError(
                f"`type `{type_name}` expects JSON `object` data but instead received: {data}"
            )

        object_data: Dict[str, JsonType] = typing.cast(Dict[str, JsonType], data)

        field_values = {}
        parsed_properties = set()
        for property_parser in self.property_parsers:
            field_values[property_parser.field_name] = property_parser.parse_field(
                object_data
            )
            parsed_properties.add(property_parser.property_name)

        unassigned_names = [
            name for name in object_data if name not in parsed_properties
        ]
        if unassigned_names:
            raise JsonKeyError(
                f"unrecognized fields in JSON object: {unassigned_names}"
            )

        return self.create(**field_values)

    def create(self, **field_values) -> object:
        "Instantiates an object with a collection of property values."

        obj: object = create_object(self.class_type)
        for field_name, field_value in field_values.items():
            setattr(obj, field_name, field_value)
        return obj


class NamedTupleDeserializer(ClassDeserializer):
    "De-serializes a named tuple from a JSON `object`."

    def __init__(self, class_type: type) -> None:
        super().__init__(class_type)

        self.property_parsers = [
            RequiredFieldDeserializer(
                field_name, field_name, create_deserializer(field_type)
            )
            for field_name, field_type in get_resolved_hints(class_type).items()
        ]

    def create(self, **field_values) -> object:
        return self.class_type(**field_values)


class DataclassDeserializer(ClassDeserializer):
    "De-serializes a data class from a JSON `object`."

    def __init__(self, class_type: type) -> None:
        super().__init__(class_type)

        self.property_parsers = []
        resolved_hints = get_resolved_hints(class_type)
        for field in dataclasses.fields(class_type):
            field_type = resolved_hints[field.name]
            property_name = python_field_to_json_property(field.name, field_type)

            is_optional = is_type_optional(field_type)
            has_default = field.default is not dataclasses.MISSING
            has_default_factory = field.default_factory is not dataclasses.MISSING

            if is_optional:
                required_type: type = unwrap_optional_type(field_type)
            else:
                required_type = field_type

            parser = create_deserializer(required_type)

            if has_default:
                field_parser: FieldDeserializer = DefaultFieldDeserializer(
                    property_name, field.name, parser, field.default
                )
            elif has_default_factory:
                default_factory = typing.cast(Callable[[], Any], field.default_factory)
                field_parser = DefaultFactoryFieldDeserializer(
                    property_name, field.name, parser, default_factory
                )
            elif is_optional:
                field_parser = OptionalFieldDeserializer(
                    property_name, field.name, parser
                )
            else:
                field_parser = RequiredFieldDeserializer(
                    property_name, field.name, parser
                )

            self.property_parsers.append(field_parser)


class TypedClassDeserializer(ClassDeserializer):
    "De-serializes a class with type annotations from a JSON `object` by iterating over class properties."

    def __init__(self, class_type: type) -> None:
        super().__init__(class_type)

        self.property_parsers = []
        for field_name, field_type in get_resolved_hints(class_type).items():
            property_name = python_field_to_json_property(field_name, field_type)

            is_optional = is_type_optional(field_type)

            if is_optional:
                required_type: type = unwrap_optional_type(field_type)
            else:
                required_type = field_type

            parser = create_deserializer(required_type)

            if is_optional:
                field_parser: FieldDeserializer = OptionalFieldDeserializer(
                    property_name, field_name, parser
                )
            else:
                field_parser = RequiredFieldDeserializer(
                    property_name, field_name, parser
                )

            self.property_parsers.append(field_parser)


def create_deserializer(typ: type) -> Deserializer:
    """
    Creates a de-serializer engine to parse an object obtained from a JSON string.

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
    """

    if isinstance(typ, type):
        return _fetch_deserializer(typ)
    else:
        # special forms are not always hashable
        return _create_deserializer(typ)


@functools.lru_cache(maxsize=None)
def _fetch_deserializer(typ: type) -> Deserializer:
    "Creates or re-uses a de-serializer engine to parse an object obtained from a JSON string."

    return _create_deserializer(typ)


def _create_deserializer(typ: type) -> Deserializer:
    "Creates a de-serializer engine to parse an object obtained from a JSON string."

    # check for well-known types
    if typ is type(None):
        return NoneDeserializer()
    elif typ is bool:
        return BoolDeserializer()
    elif typ is int:
        return IntDeserializer()
    elif typ is float:
        return FloatDeserializer()
    elif typ is str:
        return StringDeserializer()
    elif typ is bytes:
        return BytesDeserializer()
    elif typ is datetime.datetime:
        return DateTimeDeserializer()
    elif typ is datetime.date:
        return DateDeserializer()
    elif typ is datetime.time:
        return TimeDeserializer()
    elif typ is uuid.UUID:
        return UUIDDeserializer()

    # dynamically-typed collection types
    if typ is list:
        raise TypeError("explicit item type required: use `List[T]` instead of `list`")
    if typ is dict:
        raise TypeError(
            "explicit key and value types required: use `Dict[K, V]` instead of `dict`"
        )
    if typ is set:
        raise TypeError("explicit member type required: use `Set[T]` instead of `set`")
    if typ is tuple:
        raise TypeError(
            "explicit item type list required: use `Tuple[T, ...]` instead of `tuple`"
        )

    # generic types (e.g. list, dict, set, etc.)
    origin_type = typing.get_origin(typ)
    if origin_type is list:
        (list_item_type,) = typing.get_args(typ)  # unpack single tuple element
        return ListDeserializer(list_item_type)
    elif origin_type is dict:
        key_type, value_type = typing.get_args(typ)
        return DictDeserializer(key_type, value_type)
    elif origin_type is set:
        (set_member_type,) = typing.get_args(typ)  # unpack single tuple element
        return SetDeserializer(set_member_type)
    elif origin_type is tuple:
        return TupleDeserializer(typing.get_args(typ))
    elif origin_type is Union:
        return UnionDeserializer(typing.get_args(typ))

    if is_type_annotated(typ):
        return create_deserializer(unwrap_annotated_type(typ))

    if isinstance(typ, typing.ForwardRef):
        fwd: typing.ForwardRef = typ
        identifier = fwd.__forward_arg__
        evaluated_type = eval(identifier)
        return DeferredDeserializer(evaluated_type)

    if not inspect.isclass(typ):
        if is_dataclass_instance(typ):
            raise TypeError(f"dataclass type expected but got instance: {typ}")
        else:
            raise TypeError(f"unable to de-serialize unrecognized type: {typ}")

    if issubclass(typ, enum.Enum):
        return EnumDeserializer(typ)

    if is_named_tuple_type(typ):
        return NamedTupleDeserializer(typ)

    # check if object has custom serialization method
    convert_func = getattr(typ, "from_json", None)
    if callable(convert_func):
        return CustomDeserializer(convert_func)

    if is_dataclass_type(typ):
        return DataclassDeserializer(typ)
    else:
        return TypedClassDeserializer(typ)
