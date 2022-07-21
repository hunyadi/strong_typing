import dataclasses
import sys
from typing import Callable, Optional, Type, TypeVar, overload

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated  # type: ignore

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


def typeannotation(cls: type = None, *, eq=True, order=False):
    "Returns the same class as was passed in, with dunder methods added based on the fields defined in the class."

    data_cls = dataclasses.dataclass(  # type: ignore
        cls,
        init=True,
        repr=True,
        eq=eq,
        order=order,
        unsafe_hash=False,
        frozen=True,
    )
    data_cls.__repr__ = _compact_dataclass_repr
    return data_cls


@typeannotation
class Alias:
    "Alternative name of a property, typically used in JSON serialization."

    name: str


@typeannotation
class Signed:
    "Signedness of an integer type."

    is_signed: bool


@typeannotation
class Storage:
    "Number of bytes the binary representation of an integer type takes, e.g. 4 bytes for an int32."

    bytes: int


@typeannotation
class IntegerRange:
    "Minimum and maximum value of an integer. The range is inclusive."

    minimum: int
    maximum: int


@typeannotation
class Precision:
    "Precision of a floating-point value."

    significant_digits: int
    decimal_digits: int = 0

    @property
    def integer_digits(self):
        return self.significant_digits - self.decimal_digits


@typeannotation
class TimePrecision:
    """
    Precision of a timestamp or time interval.

    :param decimal_digits: Number of fractional digits retained in the seconds field for a timestamp.
    """

    decimal_digits: int = 0


@typeannotation
class MinLength:
    "Minimum length of a string."

    value: int


@typeannotation
class MaxLength:
    "Maximum length of a string."

    value: int


@typeannotation
class SpecialConversion:
    "Indicates that the annotated type is subject to custom conversion rules."


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

float32 = Annotated[float, Storage(4)]
float64 = Annotated[float, Storage(8)]

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
