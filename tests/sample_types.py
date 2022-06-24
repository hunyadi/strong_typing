from __future__ import annotations

import datetime
import enum
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

from strong_typing.auxiliary import Annotated, IntegerRange, MaxLength, Precision
from strong_typing.schema import json_schema_type


class Side(enum.Enum):
    "An enumeration with string values."

    LEFT = "L"
    RIGHT = "R"


class Suit(enum.Enum):
    "An enumeration with numeric values."

    Diamonds = 1
    Hearts = 2
    Clubs = 3
    Spades = 4


@dataclass
class SimpleValueExample:
    "A simple data class with a single property."

    value: int = 23


@dataclass
class BinaryValueExample:
    value: bytes


@json_schema_type(
    schema={
        "type": "string",
        "pattern": r"^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*$",
        "maxLength": 64,
    }
)
@dataclass
class UID:
    """A unique identifier in DICOM."""

    value: str

    def to_json(self) -> str:
        return self.value

    @classmethod
    def from_json(cls, value: str) -> UID:
        return UID(value)


class SimpleNamedTuple(NamedTuple):
    "A simple named tuple."

    int_value: int
    str_value: str


@dataclass
class SimpleObjectExample:
    "A simple data class with multiple properties."

    bool_value: bool = True
    int_value: int = 23
    float_value: float = 4.5
    str_value: str = "string"
    date_value: datetime.date = datetime.date(1970, 1, 1)
    time_value: datetime.time = datetime.time(6, 15, 30)
    datetime_value: datetime.datetime = datetime.datetime(1989, 10, 23, 1, 45, 50)
    guid_value: uuid.UUID = uuid.UUID("f81d4fae-7dec-11d0-a765-00a0c91e6bf6")


@dataclass
class AnnotatedSimpleObjectExample:
    "A simple data class with multiple properties."

    int_value: Annotated[int, IntegerRange(19, 82)] = 23
    float_value: Annotated[
        float, Precision(significant_digits=6, decimal_digits=3)
    ] = 4.5
    str_value: Annotated[str, MaxLength(64)] = "string"


@dataclass
class CompositeObjectExample:
    list_value: List[str] = field(default_factory=list)
    dict_value: Dict[str, int] = field(default_factory=dict)
    set_value: Set[int] = field(default_factory=set)
    tuple_value: Tuple[bool, int, str] = (True, 2, "three")
    named_tuple_value: SimpleNamedTuple = SimpleNamedTuple(1, "second")
    optional_value: Optional[str] = None


@dataclass
class InheritanceExample(SimpleObjectExample, CompositeObjectExample):
    extra_int_value: int = 0
    extra_str_value: str = "zero"
    extra_optional_value: Optional[str] = "value"


@dataclass
@json_schema_type
class ValueExample:
    "A value of a fundamental type wrapped into an object."

    value: int = 0


@dataclass
class NestedObjectExample:
    obj_value: CompositeObjectExample
    list_value: List[ValueExample]
    dict_value: Dict[str, ValueExample]

    def __init__(self):
        self.obj_value = CompositeObjectExample(
            list_value=["a", "b", "c"], dict_value={"key": 42}
        )
        self.list_value = [ValueExample(value=1), ValueExample(value=2)]
        self.dict_value = {
            "a": ValueExample(value=3),
            "b": ValueExample(value=4),
            "c": ValueExample(value=5),
        }
