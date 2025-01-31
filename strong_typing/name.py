"""
Type-safe data interchange for Python data classes.

:see: https://github.com/hunyadi/strong_typing
"""

import sys
import typing
from types import ModuleType
from typing import Any, Callable, Literal, Optional, Tuple

from .auxiliary import ParamSpec, _auxiliary_types
from .inspection import (
    TypeLike,
    evaluate_type,
    is_type_optional,
    is_type_union,
    unwrap_optional_type,
    unwrap_union_types,
)


class TypeFormatter:
    """
    Converts a simple, composite or generic type to a string representation.

    :param context: The module in the context of which forward references are evaluated.
    :param type_transform: Transformation to apply to types before a string is emitted, e.g. to create a link
        in a documentation.
    :param value_transform: Transformation to apply to values (e.g. in arguments to `Literal`) before a string
        is emitted.
    :param use_union_operator: Whether to emit union types as `X | Y` as per PEP 604.
    """

    context: Optional[ModuleType]
    type_transform: Optional[Callable[[type], str]]
    value_transform: Optional[Callable[[Any], str]]
    use_union_operator: bool

    def __init__(
        self,
        *,
        context: Optional[ModuleType] = None,
        type_transform: Optional[Callable[[type], str]] = None,
        value_transform: Optional[Callable[[Any], str]] = None,
        use_union_operator: bool = False,
    ) -> None:
        self.context = context
        self.type_transform = type_transform
        self.value_transform = value_transform
        self.use_union_operator = use_union_operator

    def value_to_str(self, value: Any) -> str:
        """
        Emits a string for a value, such as those in arguments to the special form `Literal`.

        :param value: Value (of any type) for which to generate a string representation.
        """

        if self.value_transform is not None:
            return self.value_transform(value)
        else:
            return repr(value)

    def union_to_str(self, data_type_args: Tuple[TypeLike, ...]) -> str:
        """
        Emits a union of types as a string.

        :param data_type_args: A tuple of `(X,Y,Z)` for a union of `X | Y | Z` or `Union[X, Y, Z]`.
        """

        if self.use_union_operator:
            return " | ".join(self.python_type_to_str(t) for t in data_type_args)
        else:
            if len(data_type_args) == 2 and type(None) in data_type_args:
                # Optional[T] is represented as Union[T, None]
                origin_name = "Optional"
                data_type_args = tuple(t for t in data_type_args if t is not type(None))
            else:
                origin_name = "Union"

            args = ", ".join(self.python_type_to_str(t) for t in data_type_args)
            return f"{origin_name}[{args}]"

    def plain_type_to_str(self, data_type: TypeLike) -> str:
        "Returns the string representation of a Python type without metadata."

        # return forward references as the annotation string
        if isinstance(data_type, typing.ForwardRef):
            fwd: typing.ForwardRef = data_type
            fwd_arg = fwd.__forward_arg__

            if self.context is None:
                return fwd_arg

            context_type = getattr(self.context, fwd_arg, None)
            if context_type is None:
                return self.python_type_to_str(evaluate_type(fwd_arg, self.context))

            if isinstance(context_type, type) and self.type_transform is not None:
                return self.type_transform(context_type)

            return fwd_arg
        elif isinstance(data_type, str):
            if self.context is None:
                raise ValueError("missing context for evaluating types")

            return self.python_type_to_str(evaluate_type(data_type, self.context))
        elif isinstance(data_type, ParamSpec):
            return data_type.__name__
        elif isinstance(data_type, typing.TypeVar):
            return data_type.__name__

        origin = typing.get_origin(data_type)
        if origin is not None:
            data_type_args = typing.get_args(data_type)

            if origin is dict:  # Dict[K, V]
                origin_name = "Dict"
            elif origin is list:  # List[T]
                origin_name = "List"
            elif origin is set:  # Set[T]
                origin_name = "Set"
            elif origin is type:  # Type[T]
                args = ", ".join(self.python_type_to_str(t) for t in data_type_args)
                return f"Type[{args}]"
            elif origin is Literal:
                args = ", ".join(self.value_to_str(arg) for arg in data_type_args)
                return f"Literal[{args}]"
            elif is_type_optional(data_type) or is_type_union(data_type):
                return self.union_to_str(data_type_args)
            else:
                origin_name = origin.__name__

            args = ", ".join(self.python_type_to_str(t) for t in data_type_args)
            return f"{origin_name}[{args}]"

        if not isinstance(data_type, type):
            raise ValueError(
                f"not a type, generic type, or type-like object: {data_type} (of type {type(data_type)})"
            )

        if self.type_transform is not None:
            return self.type_transform(data_type)
        else:
            return data_type.__name__

    def python_type_to_str(self, data_type: TypeLike) -> str:
        "Returns the string representation of a Python type."

        if data_type is None or data_type is type(None):
            return "None"
        elif data_type is Ellipsis or data_type is type(Ellipsis):
            return "..."
        elif data_type is Any:
            return "Any"
        elif isinstance(data_type, list):  # e.g. in `Callable[[bool, int], str]`
            items = ", ".join(self.python_type_to_str(item) for item in data_type)
            return f"[{items}]"

        # use compact name for alias types
        name = _auxiliary_types.get(data_type)
        if name is not None:
            return name

        metadata = getattr(data_type, "__metadata__", None)
        if metadata is not None:
            # type is Annotated[T, ...]
            metatuple: Tuple[Any, ...] = metadata
            arg = typing.get_args(data_type)[0]

            # check for auxiliary types with user-defined annotations
            metaset = set(metatuple)
            for auxiliary_type, auxiliary_name in _auxiliary_types.items():
                auxiliary_arg = typing.get_args(auxiliary_type)[0]
                if arg is not auxiliary_arg:
                    continue

                auxiliary_metatuple: Optional[Tuple[Any, ...]] = getattr(
                    auxiliary_type, "__metadata__", None
                )
                if auxiliary_metatuple is None:
                    continue

                if metaset.issuperset(auxiliary_metatuple):
                    # type is an auxiliary type with extra annotations
                    auxiliary_args = ", ".join(
                        repr(m) for m in metatuple if m not in auxiliary_metatuple
                    )
                    return f"Annotated[{auxiliary_name}, {auxiliary_args}]"

            # type is an annotated type
            args = ", ".join(repr(m) for m in metatuple)
            return f"Annotated[{self.plain_type_to_str(arg)}, {args}]"
        else:
            # type is a regular type
            return self.plain_type_to_str(data_type)


def python_type_to_str(data_type: TypeLike, *, use_union_operator: bool = False) -> str:
    """
    Returns the string representation of a Python type.

    :param use_union_operator: Whether to emit union types as `X | Y` as per PEP 604.
    """

    context = sys.modules[data_type.__module__] if isinstance(data_type, type) else None
    fmt = TypeFormatter(context=context, use_union_operator=use_union_operator)
    return fmt.python_type_to_str(data_type)


def python_type_to_name(data_type: TypeLike, *, force: bool = False) -> str:
    """
    Returns the short name of a Python type.

    :param force: Whether to produce a name for composite types such as generics.
    """

    # use compact name for alias types
    name = _auxiliary_types.get(data_type)
    if name is not None:
        return name

    # unwrap annotated types
    metadata = getattr(data_type, "__metadata__", None)
    if metadata is not None:
        # type is Annotated[T, ...]
        arg = typing.get_args(data_type)[0]
        return python_type_to_name(arg)

    if force:
        # generic types
        origin = typing.get_origin(data_type)
        if origin is not None:
            data_type_args = typing.get_args(data_type)

            if origin is dict:  # Dict[K, V]
                (key_type, value_type) = data_type_args
                key_name = python_type_to_name(key_type)
                value_name = python_type_to_name(value_type)
                return f"Dict__{key_name}__{value_name}"
            elif origin is list:  # List[T]
                (list_type,) = data_type_args  # unpack single tuple element
                item_name = python_type_to_name(list_type)
                return f"List__{item_name}"
            elif origin is set:  # Set[T]
                (set_type,) = data_type_args  # unpack single tuple element
                item_name = python_type_to_name(set_type)
                return f"Set__{item_name}"
            elif origin is type:  # Type[T]
                (type_type,) = data_type_args  # unpack single tuple element
                item_name = python_type_to_name(type_type)
                return f"Type__{item_name}"
            elif is_type_optional(data_type, strict=True):
                inner_name = python_type_to_name(unwrap_optional_type(data_type))
                return f"Optional__{inner_name}"
            elif is_type_union(data_type):
                member_types = unwrap_union_types(data_type)
                member_names = "__".join(
                    python_type_to_name(member_type) for member_type in member_types
                )
                return f"Union__{member_names}"

    # named system or user-defined type
    if hasattr(data_type, "__name__") and not typing.get_args(data_type):
        return data_type.__name__

    raise TypeError(f"cannot assign a simple name to type: {data_type}")
