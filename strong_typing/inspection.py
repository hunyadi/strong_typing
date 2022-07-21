import dataclasses
import enum
import inspect
import sys
import types
import typing
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Type, TypeVar, Union

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated  # type: ignore

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


def is_dataclass_type(typ) -> bool:
    "True if the argument corresponds to a data class type (but not an instance)."

    typ = unwrap_annotated_type(typ)
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

    typ = unwrap_annotated_type(typ)

    b = typ.__bases__
    if len(b) != 1 or b[0] != tuple:
        return False

    f = getattr(typ, "_fields", None)
    if not isinstance(f, tuple):
        return False

    return all(type(n) == str for n in f)


def is_type_enum(typ: type) -> bool:
    "True if the specified type is an enumeration type."

    typ = unwrap_annotated_type(typ)

    # use an explicit isinstance(..., type) check to filter out special forms like generics
    return isinstance(typ, type) and issubclass(typ, enum.Enum)


def is_type_optional(typ: type) -> bool:
    "True if the type annotation corresponds to an optional type (e.g. Optional[T] or Union[T1,T2,None])."

    typ = unwrap_annotated_type(typ)

    if typing.get_origin(typ) is Union:  # Optional[T] is represented as Union[T, None]
        return type(None) in typing.get_args(typ)

    return False


def is_type_union(typ: type) -> bool:
    "True if the type annotation corresponds to a union type (e.g. Union[T1,T2,T3])."

    typ = unwrap_annotated_type(typ)

    if typing.get_origin(typ) is Union:  # Optional[T] is represented as Union[T, None]
        args = typing.get_args(typ)
        return len(args) > 2 or type(None) not in args

    return False


def unwrap_optional_type(typ: Type[Optional[T]]) -> Type[T]:
    """
    Extracts the inner type of an optional type.

    :param typ: The optional type `Optional[T]`.
    :returns: The inner type `T`.
    """

    return rewrap_annotated_type(_unwrap_optional_type, typ)


def _unwrap_optional_type(typ: Type[Optional[T]]) -> Type[T]:
    "Extracts the type qualified as optional (e.g. returns `T` for `Optional[T]`)."

    # Optional[T] is represented internally as Union[T, None]
    if typing.get_origin(typ) is not Union:
        raise TypeError("optional type must have un-subscripted type of Union")

    # will automatically unwrap Union[T] into T
    return Union[
        tuple(filter(lambda item: item is not type(None), typing.get_args(typ)))  # type: ignore
    ]


def is_generic_list(typ: type) -> bool:
    "True if the specified type is a generic list, i.e. `List[T]`."

    typ = unwrap_annotated_type(typ)
    return typing.get_origin(typ) is list


def unwrap_generic_list(typ: Type[List[T]]) -> Type[T]:
    """
    Extracts the item type of a list type.

    :param typ: The list type `List[T]`.
    :returns: The item type `T`.
    """

    return rewrap_annotated_type(_unwrap_generic_list, typ)


def _unwrap_generic_list(typ: Type[List[T]]) -> Type[T]:
    "Extracts the item type of a list type (e.g. returns `T` for `List[T]`)."

    (list_type,) = typing.get_args(typ)  # unpack single tuple element
    return list_type


def is_generic_dict(typ: type) -> bool:
    "True if the specified type is a generic dictionary, i.e. `Dict[KeyType, ValueType]`."

    typ = unwrap_annotated_type(typ)
    return typing.get_origin(typ) is dict


def unwrap_generic_dict(typ: Type[Dict[K, V]]) -> Tuple[Type[K], Type[V]]:
    """
    Extracts the key and value types of a dictionary type as a tuple.

    :param typ: The dictionary type `Dict[K, V]`.
    :returns: The key and value types `K` and `V`.
    """

    return rewrap_annotated_type(_unwrap_generic_dict, typ)  # type: ignore


def _unwrap_generic_dict(typ: Type[Dict[K, V]]) -> Tuple[Type[K], Type[V]]:
    "Extracts the key and value types of a dict type (e.g. returns (`K`, `V`) for `Dict[K, V]`)."

    key_type, value_type = typing.get_args(typ)
    return key_type, value_type


def is_type_annotated(typ: type) -> bool:
    "True if the type annotation corresponds to an annotated type (i.e. `Annotated[T, ...]`)."

    return getattr(typ, "__metadata__", None) is not None


def get_annotation(data_type: type, annotation_type: Type[T]) -> Optional[T]:
    """
    Returns the first annotation on a data type that matches the expected annotation type.

    :param data_type: The annotated type from which to extract the annotation.
    :param annotation_type: The annotation class to look for.
    :returns: The annotation class instance found (if any).
    """

    if is_type_annotated(data_type):
        for annotation in data_type.__metadata__:  # type: ignore
            if isinstance(annotation, annotation_type):
                return annotation

    return None


def unwrap_annotated_type(typ: type) -> type:
    "Extracts the wrapped type from an annotated type (e.g. returns `T` for `Annotated[T, ...]`)."

    if is_type_annotated(typ):
        # type is Annotated[T, ...]
        return typing.get_args(typ)[0]
    else:
        # type is a regular type
        return typ


def rewrap_annotated_type(transform: Callable[[type], type], typ: type) -> type:
    """
    Un-boxes, transforms and re-boxes an optionally annotated type.

    :param transform: A function that maps an un-annotated type to another type.
    :param typ: A type to un-box (if necessary), transform, and re-box (if necessary).
    """

    metadata = getattr(typ, "__metadata__", None)
    if metadata is not None:
        # type is Annotated[T, ...]
        inner_type = typing.get_args(typ)[0]
    else:
        # type is a regular type
        inner_type = typ

    transformed_type = transform(inner_type)

    if metadata is not None:
        return Annotated[(transformed_type, *metadata)]  # type: ignore
    else:
        return transformed_type


def get_module_classes(module: types.ModuleType) -> List[type]:
    "Returns all classes declared in a module."

    is_class_member = (
        lambda member: inspect.isclass(member) and member.__module__ == module.__name__
    )
    return [class_type for _, class_type in inspect.getmembers(module, is_class_member)]


def get_class_properties(typ: type) -> Iterable[Tuple[str, type]]:
    "Returns all properties of a class."

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


def get_referenced_types(typ: type) -> List[type]:
    """
    Extracts types indirectly referenced by this type.

    For example, extract `T` from `List[T]`, `Optional[T]` or `Annotated[T, ...]`, `K` and `V` from `Dict[K,V]`,
    `A` and `B` from `Union[A,B]`.
    """

    metadata = getattr(typ, "__metadata__", None)
    if metadata is not None:
        # type is Annotated[T, ...]
        arg = typing.get_args(typ)[0]
        return get_referenced_types(arg)

    # type is a regular type
    result = []
    origin = typing.get_origin(typ)
    if origin is not None:
        for arg in typing.get_args(typ):
            result.extend(get_referenced_types(arg))
    elif typ is not type(None):
        result.append(typ)

    return result
