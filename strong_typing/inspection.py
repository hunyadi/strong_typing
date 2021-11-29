import dataclasses
import enum
import inspect
import sys
import types
import typing
from typing import Dict, Iterable, List, Optional, Tuple, Type, TypeVar, Union

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


def get_module_classes(module: types.ModuleType) -> List[Type]:
    is_class_member = (
        lambda member: inspect.isclass(member) and member.__module__ == module.__name__
    )
    return [class_type for _, class_type in inspect.getmembers(module, is_class_member)]


def get_class_properties(typ: Type) -> Iterable[Tuple[str, Type]]:
    if sys.version_info >= (3, 9):
        resolved_hints = typing.get_type_hints(typ, include_extras=True)
    else:
        resolved_hints = typing.get_type_hints(typ)

    if is_dataclass_type(typ):
        return (
            (field.name, resolved_hints[field.name])
            for field in dataclasses.fields(typ)
        )
    else:
        return resolved_hints.items()
