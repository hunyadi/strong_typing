import dataclasses
import sys
from dataclasses import dataclass
from typing import Callable, Optional, Type, TypeVar, overload

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

T = TypeVar("T")


def _compact_dataclass_repr(obj) -> str:
    "Compact dataclass representation where positional arguments are used instead of keyword arguments."

    arglist = ", ".join(
        repr(getattr(obj, field.name)) for field in dataclasses.fields(obj)
    )
    return f"{obj.__class__.__name__}({arglist})"


class CompactDataClass:
    "A data class whose repr() uses positional rather than keyword arguments."

    def __repr__(self) -> str:
        return _compact_dataclass_repr(self)


@overload
def typeannotation(cls: Type[T], /) -> Type[T]:
    ...


@overload
def typeannotation(
    cls: None, *, eq: bool = True, order: bool = False
) -> Callable[[Type[T]], Type[T]]:
    ...


def typeannotation(cls: Type[T] = None, *, eq=True, order=False):
    "Returns the same class as was passed in, with dunder methods added based on the fields defined in the class."

    def wrap(cls: Type[T]) -> Type[T]:
        setattr(cls, "__repr__", _compact_dataclass_repr)
        if not dataclasses.is_dataclass(cls):
            cls = dataclasses.dataclass(  # type: ignore
                cls,
                init=True,
                repr=False,
                eq=eq,
                order=order,
                unsafe_hash=False,
                frozen=True,
            )
        return cls

    # see if decorator is used as @typeannotation or @typeannotation()
    if cls is None:
        # called with parentheses
        return wrap
    else:
        # called without parentheses
        return wrap(cls)


@typeannotation
@dataclass(frozen=True)
class Alias:
    "Alternative name of a property, typically used in JSON serialization."

    name: str


@typeannotation
@dataclass(frozen=True)
class Signed:
    "Signedness of an integer type."

    is_signed: bool


@typeannotation
@dataclass(frozen=True)
class Storage:
    "Number of bytes the binary representation of an integer type takes, e.g. 4 bytes for an int32."

    bytes: int


@typeannotation
@dataclass(frozen=True)
class IntegerRange:
    "Minimum and maximum value of an integer. The range is inclusive."

    minimum: int
    maximum: int


@typeannotation
@dataclass(frozen=True)
class Precision:
    "Precision of a floating-point value."

    significant_digits: int
    decimal_digits: int = 0

    @property
    def integer_digits(self):
        return self.significant_digits - self.decimal_digits


@typeannotation
@dataclass(frozen=True)
class TimePrecision:
    """
    Precision of a timestamp or time interval.

    :param decimal_digits: Number of fractional digits retained in the seconds field for a timestamp.
    """

    decimal_digits: int = 0


@typeannotation
@dataclass(frozen=True)
class MinLength:
    "Minimum length of a string."

    value: int


@typeannotation
@dataclass(frozen=True)
class MaxLength:
    "Maximum length of a string."

    value: int


@typeannotation
@dataclass(frozen=True)
class SpecialConversion:
    "Indicates that the annotated type is subject to custom conversion rules."


int8: TypeAlias = Annotated[int, Signed(True), Storage(1), IntegerRange(-128, 127)]
int16: TypeAlias = Annotated[int, Signed(True), Storage(2), IntegerRange(-32768, 32767)]
int32: TypeAlias = Annotated[
    int,
    Signed(True),
    Storage(4),
    IntegerRange(-2147483648, 2147483647),
]
int64: TypeAlias = Annotated[
    int,
    Signed(True),
    Storage(8),
    IntegerRange(-9223372036854775808, 9223372036854775807),
]

uint8: TypeAlias = Annotated[int, Signed(False), Storage(1), IntegerRange(0, 255)]
uint16: TypeAlias = Annotated[int, Signed(False), Storage(2), IntegerRange(0, 65535)]
uint32: TypeAlias = Annotated[
    int,
    Signed(False),
    Storage(4),
    IntegerRange(0, 4294967295),
]
uint64: TypeAlias = Annotated[
    int,
    Signed(False),
    Storage(8),
    IntegerRange(0, 18446744073709551615),
]

float32: TypeAlias = Annotated[float, Storage(4)]
float64: TypeAlias = Annotated[float, Storage(8)]

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
