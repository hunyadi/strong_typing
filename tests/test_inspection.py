import datetime
import enum
import sys
import unittest
from dataclasses import dataclass
from typing import Annotated, Any, NamedTuple, Optional, Union

from strong_typing.auxiliary import typeannotation
from strong_typing.inspection import (
    check_recursive,
    get_class_properties,
    get_module_classes,
    get_referenced_types,
    is_dataclass_type,
    is_generic_dict,
    is_generic_instance,
    is_generic_list,
    is_named_tuple_type,
    is_type_enum,
    is_type_optional,
    is_type_union,
    unwrap_generic_dict,
    unwrap_generic_list,
    unwrap_union_types,
)

from .sample_types import CompositeDataclass, NestedDataclass, SimpleDataclass


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


class SimpleObject:
    "A value of a fundamental type wrapped into an object."

    value: int = 0


@dataclass
class SimpleDataClass:
    "A value of a fundamental type wrapped into an object."

    value: int = 0


class SimpleNamedTuple(NamedTuple):
    integer: int
    string: str


@typeannotation
class SimpleAnnotation:
    pass


class TestInspection(unittest.TestCase):
    def test_simple(self) -> None:
        module = sys.modules[self.__module__]
        self.assertSetEqual(get_referenced_types(type(None), module), set())
        self.assertSetEqual(get_referenced_types(Any, module), set())
        self.assertSetEqual(get_referenced_types(int, module), set([int]))
        self.assertSetEqual(get_referenced_types(Optional[str], module), set([str]))
        self.assertSetEqual(get_referenced_types(list[str], module), set([str]))
        self.assertSetEqual(get_referenced_types(list[list[str]], module), set([str]))
        self.assertSetEqual(get_referenced_types(list[Optional[str]], module), set([str]))
        self.assertSetEqual(get_referenced_types(dict[int, bool], module), set([int, bool]))
        self.assertSetEqual(get_referenced_types(Union[int, bool, str], module), set([int, bool, str]))
        self.assertSetEqual(
            get_referenced_types(Union[None, int, datetime.datetime], module),
            set([int, datetime.datetime]),
        )

    def test_enum(self) -> None:
        self.assertTrue(is_type_enum(Side))
        self.assertTrue(is_type_enum(Suit))
        self.assertFalse(is_type_enum(Side.LEFT))
        self.assertFalse(is_type_enum(Suit.Diamonds))
        self.assertFalse(is_type_enum(int))
        self.assertFalse(is_type_enum(str))
        self.assertFalse(is_type_enum(SimpleObject))

    def test_optional(self) -> None:
        self.assertTrue(is_type_optional(Optional[int]))
        self.assertTrue(is_type_optional(Union[None, int]))
        self.assertTrue(is_type_optional(Union[int, None]))

        if sys.version_info >= (3, 10):
            self.assertTrue(is_type_optional(None | int))
            self.assertTrue(is_type_optional(int | None))

        self.assertFalse(is_type_optional(int))
        self.assertFalse(is_type_optional(Union[int, str]))

    def test_strict_optional(self) -> None:
        self.assertTrue(is_type_optional(Union[None, int], strict=True))
        self.assertTrue(is_type_optional(Union[int, None], strict=True))
        self.assertTrue(is_type_optional(Union[None, int, str]))
        self.assertTrue(is_type_optional(Union[int, None, str]))
        self.assertFalse(is_type_optional(Union[None, int, str], strict=True))
        self.assertFalse(is_type_optional(Union[int, None, str], strict=True))

    def test_union(self) -> None:
        self.assertTrue(is_type_union(Union[int, str]))
        self.assertTrue(is_type_union(Union[bool, int, str]))
        self.assertTrue(is_type_union(Union[int, str, None]))
        self.assertTrue(is_type_union(Union[bool, int, str, None]))

        if sys.version_info >= (3, 10):
            self.assertTrue(is_type_union(int | str))
            self.assertTrue(is_type_union(bool | int | str))
            self.assertTrue(is_type_union(int | str | None))
            self.assertTrue(is_type_union(bool | int | str | None))

        self.assertFalse(is_type_union(int))

        self.assertEqual(unwrap_union_types(Union[int, str]), (int, str))
        self.assertEqual(unwrap_union_types(Union[int, str, None]), (int, str, type(None)))
        if sys.version_info >= (3, 10):
            self.assertEqual(unwrap_union_types(int | str), (int, str))
            self.assertEqual(unwrap_union_types(int | str | None), (int, str, type(None)))

    def test_list(self) -> None:
        self.assertTrue(is_generic_list(list[int]))
        self.assertTrue(is_generic_list(list[str]))
        self.assertTrue(is_generic_list(list[SimpleObject]))
        self.assertFalse(is_generic_list(list))
        self.assertFalse(is_generic_list([]))

        self.assertEqual(unwrap_generic_list(list[int]), int)
        self.assertEqual(unwrap_generic_list(list[str]), str)
        self.assertEqual(unwrap_generic_list(list[list[str]]), list[str])

    def test_dict(self) -> None:
        self.assertTrue(is_generic_dict(dict[int, str]))
        self.assertTrue(is_generic_dict(dict[str, SimpleObject]))
        self.assertFalse(is_generic_dict(dict))
        self.assertFalse(is_generic_dict({}))

        self.assertEqual(unwrap_generic_dict(dict[int, str]), (int, str))
        self.assertEqual(unwrap_generic_dict(dict[str, SimpleObject]), (str, SimpleObject))
        self.assertEqual(
            unwrap_generic_dict(dict[str, list[SimpleObject]]),
            (str, list[SimpleObject]),
        )

    def test_annotated(self) -> None:
        self.assertTrue(is_type_enum(Annotated[Suit, SimpleAnnotation()]))
        self.assertTrue(is_generic_list(Annotated[list[int], SimpleAnnotation()]))
        self.assertTrue(is_generic_dict(Annotated[dict[int, str], SimpleAnnotation()]))

    def test_classes(self) -> None:
        classes = get_module_classes(sys.modules[__name__])
        self.assertCountEqual(
            classes,
            [
                Side,
                Suit,
                SimpleAnnotation,
                SimpleObject,
                SimpleDataClass,
                SimpleNamedTuple,
                TestInspection,
            ],
        )

    def test_properties(self) -> None:
        properties = [(name, data_type) for name, data_type in get_class_properties(SimpleObject)]
        self.assertCountEqual(properties, [("value", int)])

        self.assertTrue(is_dataclass_type(SimpleDataClass))
        properties = [(name, data_type) for name, data_type in get_class_properties(SimpleDataClass)]
        self.assertCountEqual(properties, [("value", int)])

        self.assertTrue(is_named_tuple_type(SimpleNamedTuple))
        properties = [(name, data_type) for name, data_type in get_class_properties(SimpleNamedTuple)]
        self.assertCountEqual(properties, [("integer", int), ("string", str)])

    def test_generic(self) -> None:
        obj = SimpleObject()
        self.assertTrue(is_generic_instance(obj, SimpleObject))
        self.assertFalse(is_generic_instance(None, SimpleObject))
        self.assertFalse(is_generic_instance(42, SimpleObject))
        self.assertFalse(is_generic_instance("string", SimpleObject))

        self.assertTrue(is_generic_instance([], list[int]))
        self.assertTrue(is_generic_instance([1, 2, 3], list[int]))
        self.assertTrue(is_generic_instance([obj], list[SimpleObject]))
        self.assertFalse(is_generic_instance(None, list[int]))
        self.assertFalse(is_generic_instance(42, list[int]))

        self.assertTrue(is_generic_instance({}, dict[str, int]))
        self.assertTrue(is_generic_instance({"a": 1, "b": 2}, dict[str, int]))
        self.assertFalse(is_generic_instance(None, dict[str, int]))
        self.assertFalse(is_generic_instance("string", dict[str, int]))

        self.assertTrue(is_generic_instance(set(), set[int]))
        self.assertTrue(is_generic_instance(set([1, 2, 3]), set[int]))
        self.assertFalse(is_generic_instance(None, set[int]))
        self.assertFalse(is_generic_instance(42, set[int]))

        self.assertTrue(is_generic_instance(("a", 42), tuple[str, int]))
        self.assertFalse(is_generic_instance(None, tuple[str, int]))

        self.assertTrue(is_generic_instance("string", Union[str, int]))
        self.assertTrue(is_generic_instance(42, Union[str, int]))
        self.assertFalse(is_generic_instance(None, Union[str, int]))

        self.assertTrue(is_generic_instance(None, Optional[str]))
        self.assertTrue(is_generic_instance("string", Optional[str]))
        self.assertFalse(is_generic_instance(42, Optional[str]))

    def test_recursive(self) -> None:
        self.assertTrue(
            check_recursive(
                SimpleObject(),
                pred=lambda typ, obj: isinstance(obj, typ),
            )
        )
        self.assertTrue(
            check_recursive(
                SimpleDataClass(),
                pred=lambda typ, obj: isinstance(obj, typ),
            )
        )
        self.assertTrue(
            check_recursive(
                SimpleDataclass(),
                pred=lambda typ, obj: isinstance(obj, typ),
            )
        )
        self.assertTrue(
            check_recursive(
                CompositeDataclass(),
                pred=lambda typ, obj: is_generic_instance(obj, typ),
            )
        )
        self.assertTrue(
            check_recursive(
                NestedDataclass(),
                pred=lambda typ, obj: is_generic_instance(obj, typ),
            )
        )
        self.assertTrue(
            check_recursive(
                SimpleDataclass(),
                type_pred=lambda typ: typ is datetime.datetime,
                value_pred=lambda obj: obj.tzinfo is not None,
            )
        )


if __name__ == "__main__":
    unittest.main()
