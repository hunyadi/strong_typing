import dataclasses
import sys
import typing
from dataclasses import dataclass
from typing import Optional, Union

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated


class CompactDataClass:
    "A data class whose repr() uses positional rather than keyword arguments."

    def __repr__(self) -> str:
        arglist = ", ".join(
            repr(getattr(self, field.name)) for field in dataclasses.fields(self)
        )
        return f"{self.__class__.__name__}({arglist})"


@dataclass(frozen=True, repr=False)
class Signed(CompactDataClass):
    is_signed: bool


@dataclass(frozen=True, repr=False)
class Storage(CompactDataClass):
    bytes: int


@dataclass(frozen=True, repr=False)
class IntegerRange(CompactDataClass):
    minimum: int
    maximum: int


@dataclass(frozen=True, repr=False)
class Precision(CompactDataClass):
    significant_digits: int
    decimal_digits: Optional[int] = 0

    @property
    def integer_digits(self):
        return self.significant_digits - self.decimal_digits


@dataclass(frozen=True, repr=False)
class MinLength(CompactDataClass):
    value: int


@dataclass(frozen=True, repr=False)
class MaxLength(CompactDataClass):
    value: int


int8 = Annotated[int, Signed(True), Storage(1), IntegerRange(-128, 127)]
int16 = Annotated[int, Signed(True), Storage(2), IntegerRange(-32768, 32767)]
int32 = Annotated[int, Signed(True), Storage(4), IntegerRange(-2147483648, 2147483647)]
int64 = Annotated[
    int,
    Signed(True),
    Storage(8),
    IntegerRange(-9223372036854775808, 9223372036854775807),
]

uint8 = Annotated[int, Signed(False), Storage(1), IntegerRange(0, 255)]
uint16 = Annotated[int, Signed(False), Storage(2), IntegerRange(0, 65535)]
uint32 = Annotated[int, Signed(False), Storage(4), IntegerRange(0, 4294967295)]
uint64 = Annotated[
    int, Signed(False), Storage(8), IntegerRange(0, 18446744073709551615)
]

# maps globals of type Annotation[T, ...] defined in this module to their string names
_auxiliary_types = {}
module = sys.modules[__name__]
for var in dir(module):
    typ = getattr(module, var)
    if getattr(typ, "__metadata__", None) is not None:
        # type is Annotation[T, ...]
        _auxiliary_types[typ] = var


def get_auxiliary_format(data_type: type) -> Optional[str]:
    "Returns the JSON format string corresponding to an auxiliary type."

    return _auxiliary_types.get(data_type)


def _python_type_to_str(data_type: type) -> str:
    "Returns the string representation of a Python type without metadata."

    origin = typing.get_origin(data_type)
    if origin is not None:
        args = ", ".join(python_type_to_str(t) for t in typing.get_args(data_type))

        if origin is dict:  # Dict[T]
            origin_name = "Dict"
        elif origin is list:  # List[T]
            origin_name = "List"
        elif origin is set:  # Set[T]
            origin_name = "Set"
        elif origin is Union:
            origin_name = "Union"
        else:
            origin_name = origin.__name__

        return f"{origin_name}[{args}]"

    if isinstance(data_type, typing.ForwardRef):
        fwd: typing.ForwardRef = data_type
        return fwd.__forward_arg__

    return data_type.__name__


def python_type_to_str(data_type: type) -> str:
    "Returns the string representation of a Python type."

    # use compact name for alias types
    name = _auxiliary_types.get(data_type)
    if name is not None:
        return name

    metadata = getattr(data_type, "__metadata__", None)
    if metadata is not None:
        # type is Annotated[T, ...]
        arg = typing.get_args(data_type)[0]
        s = _python_type_to_str(arg)
        args = ", ".join(repr(m) for m in metadata)
        return f"Annotated[{s}, {args}]"
    else:
        # type is a regular type
        return _python_type_to_str(data_type)


def python_type_to_name(data_type: type) -> str:
    "Returns the short name of a Python type."

    # use compact name for alias types
    name = _auxiliary_types.get(data_type)
    if name is not None:
        return name

    metadata = getattr(data_type, "__metadata__", None)
    if metadata is not None:
        # type is Annotated[T, ...]
        arg = typing.get_args(data_type)[0]
        return arg.__name__
    else:
        return data_type.__name__
