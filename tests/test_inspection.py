import datetime
import enum
import unittest
from typing import Dict, List, Optional, Union

from strong_typing.auxiliary import Annotated, typeannotation
from strong_typing.inspection import (
    get_referenced_types,
    is_generic_dict,
    is_generic_list,
    is_type_enum,
    unwrap_generic_dict,
    unwrap_generic_list,
)


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


@typeannotation
class SimpleAnnotation:
    pass


class TestInspection(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(get_referenced_types(type(None)), [])
        self.assertEqual(get_referenced_types(int), [int])
        self.assertEqual(get_referenced_types(Optional[str]), [str])
        self.assertEqual(get_referenced_types(List[str]), [str])
        self.assertEqual(get_referenced_types(Dict[int, bool]), [int, bool])
        self.assertEqual(get_referenced_types(Union[int, bool, str]), [int, bool, str])
        self.assertEqual(
            get_referenced_types(Union[None, int, datetime.datetime]),
            [int, datetime.datetime],
        )

    def test_enum(self):
        self.assertTrue(is_type_enum(Side))
        self.assertTrue(is_type_enum(Suit))
        self.assertFalse(is_type_enum(Side.LEFT))
        self.assertFalse(is_type_enum(Suit.Diamonds))
        self.assertFalse(is_type_enum(int))
        self.assertFalse(is_type_enum(str))
        self.assertFalse(is_type_enum(SimpleObject))

    def test_list(self):
        self.assertTrue(is_generic_list(List[int]))
        self.assertTrue(is_generic_list(List[str]))
        self.assertTrue(is_generic_list(List[SimpleObject]))
        self.assertFalse(is_generic_list(list))
        self.assertFalse(is_generic_list([]))

        self.assertEqual(unwrap_generic_list(List[int]), int)
        self.assertEqual(unwrap_generic_list(List[str]), str)
        self.assertEqual(unwrap_generic_list(List[List[str]]), List[str])

    def test_dict(self):
        self.assertTrue(is_generic_dict(Dict[int, str]))
        self.assertTrue(is_generic_dict(Dict[str, SimpleObject]))
        self.assertFalse(is_generic_dict(dict))
        self.assertFalse(is_generic_dict({}))

        self.assertEqual(unwrap_generic_dict(Dict[int, str]), (int, str))
        self.assertEqual(
            unwrap_generic_dict(Dict[str, SimpleObject]), (str, SimpleObject)
        )
        self.assertEqual(
            unwrap_generic_dict(Dict[str, List[SimpleObject]]),
            (str, List[SimpleObject]),
        )

    def test_annotated(self):
        self.assertTrue(is_type_enum(Annotated[Suit, SimpleAnnotation()]))
        self.assertTrue(is_generic_list(Annotated[List[int], SimpleAnnotation()]))
        self.assertTrue(is_generic_dict(Annotated[Dict[int, str], SimpleAnnotation()]))


if __name__ == "__main__":
    unittest.main()
