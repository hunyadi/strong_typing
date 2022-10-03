import dataclasses
import datetime
import enum
import inspect
import re
import sys
import types
import typing
import uuid
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    from typing_extensions import TypeGuard

S = TypeVar("S")
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


def is_named_tuple_instance(obj: object) -> TypeGuard[NamedTuple]:
    "True if the argument corresponds to a named tuple instance."

    return is_named_tuple_type(type(obj))


def is_named_tuple_type(typ: type) -> TypeGuard[Type[NamedTuple]]:
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


def is_type_enum(typ: type) -> TypeGuard[Type[enum.Enum]]:
    "True if the specified type is an enumeration type."

    typ = unwrap_annotated_type(typ)

    # use an explicit isinstance(..., type) check to filter out special forms like generics
    return isinstance(typ, type) and issubclass(typ, enum.Enum)


def enum_value_types(enum_type: Type[enum.Enum]) -> List[type]:
    """
    Returns all unique value types of the `enum.Enum` type in definition order.
    """

    # filter unique enumeration value types by keeping definition order
    return list(dict.fromkeys(type(e.value) for e in enum_type))


def _is_union_like(typ: type) -> bool:
    "True if type is a union such as `Union[T1, T2, ...]` or a union type `T1 | T2`."

    is_generic_union = typing.get_origin(typ) is Union
    is_union_expr = sys.version_info >= (3, 10) and isinstance(typ, types.UnionType)
    return is_generic_union or is_union_expr


def is_type_optional(typ: type, strict: bool = False) -> TypeGuard[Type[Optional[Any]]]:
    """
    True if the type annotation corresponds to an optional type (e.g. `Optional[T]` or `Union[T1,T2,None]`).

    `Optional[T]` is represented as `Union[T, None]` is classic style, and is equivalent to `T | None` in new style.

    :param strict: True if only `Optional[T]` qualifies as an optional type but `Union[T1, T2, None]` does not.
    """

    typ = unwrap_annotated_type(typ)

    if _is_union_like(typ):
        args = typing.get_args(typ)
        if strict and len(args) != 2:
            return False

        return type(None) in args

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


def is_type_union(typ: type) -> bool:
    "True if the type annotation corresponds to a union type (e.g. `Union[T1,T2,T3]`)."

    typ = unwrap_annotated_type(typ)

    if _is_union_like(typ):
        args = typing.get_args(typ)
        return len(args) > 2 or type(None) not in args

    return False


def unwrap_union_types(typ: type) -> Tuple[type, ...]:
    """
    Extracts the inner types of a union type.

    :param typ: The union type `Union[T1, T2, ...]`.
    :returns: The inner types `T1`, `T2`, etc.
    """

    return _unwrap_union_types(typ)


def _unwrap_union_types(typ: type) -> Tuple[type, ...]:
    "Extracts the types in a union (e.g. returns a tuple of types `T1` and `T2` for `Union[T1, T2]`)."

    if typing.get_origin(typ) is not Union:
        raise TypeError("union type must have un-subscripted type of Union")

    # will automatically unwrap Union[T] into T
    return typing.get_args(typ)


def is_type_literal(typ: type) -> bool:
    "True if the specified type is a literal of one or more constant values, e.g. `Literal['string']` or `Literal[42]`."

    typ = unwrap_annotated_type(typ)
    return typing.get_origin(typ) is Literal


def unwrap_literal_values(typ: type) -> Tuple[Any, ...]:
    """
    Extracts the constant values captured by a literal type.

    :param typ: The literal type `Literal[value, ...]`.
    :returns: A tuple of values captured by the literal type.
    """

    typ = unwrap_annotated_type(typ)
    return typing.get_args(typ)


def unwrap_literal_types(typ: type) -> Tuple[type, ...]:
    """
    Extracts the types of the constant values captured by a literal type.

    :param typ: The literal type `Literal[value, ...]`.
    :returns: A tuple of item types `T` such that `type(value) == T`.
    """

    return tuple(type(t) for t in unwrap_literal_values(typ))


def is_generic_list(typ: type) -> TypeGuard[Type[list]]:
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


def is_generic_dict(typ: type) -> TypeGuard[Type[dict]]:
    "True if the specified type is a generic dictionary, i.e. `Dict[KeyType, ValueType]`."

    typ = unwrap_annotated_type(typ)
    return typing.get_origin(typ) is dict


def unwrap_generic_dict(typ: Type[Dict[K, V]]) -> Tuple[Type[K], Type[V]]:
    """
    Extracts the key and value types of a dictionary type as a tuple.

    :param typ: The dictionary type `Dict[K, V]`.
    :returns: The key and value types `K` and `V`.
    """

    return _unwrap_generic_dict(unwrap_annotated_type(typ))


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

    metadata = getattr(data_type, "__metadata__", None)
    if metadata is not None:
        for annotation in metadata:
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


def rewrap_annotated_type(
    transform: Callable[[Type[S]], Type[T]], typ: Type[S]
) -> Type[T]:
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
    "Returns all classes declared directly in a module."

    is_class_member = (
        lambda member: inspect.isclass(member) and member.__module__ == module.__name__
    )
    return [class_type for _, class_type in inspect.getmembers(module, is_class_member)]


def get_resolved_hints(typ: type) -> Dict[str, type]:
    if sys.version_info >= (3, 9):
        return typing.get_type_hints(typ, include_extras=True)
    else:
        return typing.get_type_hints(typ)


def get_class_properties(typ: type) -> Iterable[Tuple[str, type]]:
    "Returns all properties of a class."

    resolved_hints = get_resolved_hints(typ)

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


def get_signature(fn: Callable[..., Any]) -> inspect.Signature:
    "Extracts the signature of a function."

    if sys.version_info >= (3, 10):
        return inspect.signature(fn, eval_str=True)
    else:
        return inspect.signature(fn)


def is_reserved_property(name: str) -> bool:
    "True if the name stands for an internal property."

    # filter built-in and special properties
    if re.match(r"^__.+__$", name):
        return True

    # filter built-in special names
    if name in ["_abc_impl"]:
        return True

    return False


def create_object(typ: Type[T]) -> T:
    if issubclass(typ, Exception):
        e = typ.__new__(typ)
        return typing.cast(T, e)
    else:
        return object.__new__(typ)


def is_generic_instance(obj: Any, typ: type) -> bool:
    """
    Returns whether an object is an instance of a generic class, a standard class or of a subclass thereof.

    This function checks the following items recursively:
    * items of a list
    * keys and values of a dictionary
    * members of a set
    * items of a tuple
    * members of a union type

    :param obj: The (possibly generic container) object to check recursively.
    :param typ: The expected type of the object.
    """

    if isinstance(typ, typing.ForwardRef):
        fwd: typing.ForwardRef = typ
        identifier = fwd.__forward_arg__
        typ = eval(identifier)
        return is_generic_instance(obj, typ)

    # generic types (e.g. list, dict, set, etc.)
    origin_type = typing.get_origin(typ)
    if origin_type is list:
        if not isinstance(obj, list):
            return False
        (list_item_type,) = typing.get_args(typ)  # unpack single tuple element
        list_obj: list = obj
        return all(is_generic_instance(item, list_item_type) for item in list_obj)
    elif origin_type is dict:
        if not isinstance(obj, dict):
            return False
        key_type, value_type = typing.get_args(typ)
        dict_obj: dict = obj
        return all(
            is_generic_instance(key, key_type)
            and is_generic_instance(value, value_type)
            for key, value in dict_obj.items()
        )
    elif origin_type is set:
        if not isinstance(obj, set):
            return False
        (set_member_type,) = typing.get_args(typ)  # unpack single tuple element
        set_obj: set = obj
        return all(is_generic_instance(item, set_member_type) for item in set_obj)
    elif origin_type is tuple:
        if not isinstance(obj, tuple):
            return False
        return all(
            is_generic_instance(item, tuple_item_type)
            for tuple_item_type, item in zip(
                (tuple_item_type for tuple_item_type in typing.get_args(typ)),
                (item for item in obj),
            )
        )
    elif origin_type is Union:
        return any(
            is_generic_instance(obj, member_type)
            for member_type in typing.get_args(typ)
        )
    elif isinstance(typ, type):
        return isinstance(obj, typ)
    else:
        raise TypeError(f"expected `type` but got: {typ}")


class RecursiveChecker:
    _pred: Optional[Callable[[type, Any], bool]]

    def __init__(self, pred: Callable[[type, Any], bool]) -> None:
        """
        Creates a checker to verify if a predicate applies to all nested member properties of an object recursively.

        :param pred: The predicate to test on member properties. Takes a property type and a property value.
        """

        self._pred = pred

    def pred(self, typ: type, obj: Any) -> bool:
        "Acts as a workaround for the type checker mypy."

        assert self._pred is not None
        return self._pred(typ, obj)

    def check(self, typ: type, obj: Any) -> bool:
        """
        Checks if a predicate applies to all nested member properties of an object recursively.

        :param typ: The type to recurse into.
        :param obj: The object to inspect recursively. Must be an instance of the given type.
        :returns: True if all member properties pass the filter predicate.
        """

        # check for well-known types
        if (
            typ is type(None)
            or typ is bool
            or typ is int
            or typ is float
            or typ is str
            or typ is bytes
            or typ is datetime.datetime
            or typ is datetime.date
            or typ is datetime.time
            or typ is uuid.UUID
        ):
            return self.pred(typ, obj)

        # generic types (e.g. list, dict, set, etc.)
        origin_type = typing.get_origin(typ)
        if origin_type is list:
            if not isinstance(obj, list):
                raise TypeError(f"expected `list` but got: {obj}")
            (list_item_type,) = typing.get_args(typ)  # unpack single tuple element
            list_obj: list = obj
            return all(self.check(list_item_type, item) for item in list_obj)
        elif origin_type is dict:
            if not isinstance(obj, dict):
                raise TypeError(f"expected `dict` but got: {obj}")
            key_type, value_type = typing.get_args(typ)
            dict_obj: dict = obj
            return all(self.check(value_type, item) for item in dict_obj.values())
        elif origin_type is set:
            if not isinstance(obj, set):
                raise TypeError(f"expected `set` but got: {obj}")
            (set_member_type,) = typing.get_args(typ)  # unpack single tuple element
            set_obj: set = obj
            return all(self.check(set_member_type, item) for item in set_obj)
        elif origin_type is tuple:
            if not isinstance(obj, tuple):
                raise TypeError(f"expected `tuple` but got: {obj}")
            return all(
                self.check(tuple_item_type, item)
                for tuple_item_type, item in zip(
                    (tuple_item_type for tuple_item_type in typing.get_args(typ)),
                    (item for item in obj),
                )
            )
        elif origin_type is Union:
            return self.pred(typ, obj)

        if not inspect.isclass(typ):
            raise TypeError(f"expected `type` but got: {typ}")

        # enumeration type
        if issubclass(typ, enum.Enum):
            if not isinstance(obj, enum.Enum):
                raise TypeError(f"expected `{typ}` but got: {obj}")
            return self.pred(typ, obj)

        # class types with properties
        if is_named_tuple_type(typ):
            if not isinstance(obj, tuple):
                raise TypeError(f"expected `NamedTuple` but got: {obj}")
            return all(
                self.check(field_type, getattr(obj, field_name))
                for field_name, field_type in typing.get_type_hints(typ).items()
            )
        elif is_dataclass_type(typ):
            if not isinstance(obj, typ):
                raise TypeError(f"expected `{typ}` but got: {obj}")
            resolved_hints = get_resolved_hints(typ)
            return all(
                self.check(resolved_hints[field.name], getattr(obj, field.name))
                for field in dataclasses.fields(typ)
            )
        else:
            if not isinstance(obj, typ):
                raise TypeError(f"expected `{typ}` but got: {obj}")
            return all(
                self.check(property_type, getattr(obj, property_name))
                for property_name, property_type in get_class_properties(typ)
            )


def check_recursive(
    obj: Any,
    /,
    *,
    pred: Callable[[Type[T], T], bool] = None,
    type_pred: Callable[[Type[T]], bool] = None,
    value_pred: Callable[[T], bool] = None,
) -> bool:
    """
    Checks if a predicate applies to all nested member properties of an object recursively.

    :param typ: The type to recurse into.
    :param obj: The object to inspect recursively. Must be an instance of the given type.
    :param pred: The predicate to test on member properties. Takes a property type and a property value.
    :param type_pred: Constrains the check to properties of an expected type. Properties of other types pass automatically.
    :param value_pred: Verifies a condition on member property values (of an expected type).
    :returns: True if all member properties pass the filter predicate(s).
    """

    if type_pred is not None and value_pred is not None:
        if pred is not None:
            raise TypeError(
                "filter predicate not permitted when type and value predicates are present"
            )

        type_p: Callable[[Type[T]], bool] = type_pred
        value_p: Callable[[T], bool] = value_pred
        pred = lambda typ, obj: not type_p(typ) or value_p(obj)

    elif value_pred is not None:
        if pred is not None:
            raise TypeError(
                "filter predicate not permitted when value predicate is present"
            )

        value_only_p: Callable[[T], bool] = value_pred
        pred = lambda typ, obj: value_only_p(obj)

    elif type_pred is not None:
        raise TypeError("value predicate required when type predicate is present")

    elif pred is None:
        pred = lambda typ, obj: True

    return RecursiveChecker(pred).check(type(obj), obj)
