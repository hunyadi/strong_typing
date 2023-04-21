import datetime
import decimal
import unittest
import uuid
from dataclasses import dataclass
from typing import Dict, List, Set, TypeVar

from strong_typing.inspection import is_dataclass_type
from strong_typing.topological import topological_sort, type_topological_sort

T = TypeVar("T")


class SimpleClass:
    boolean: bool
    integer: int
    string: str
    timestamp: datetime.datetime


@dataclass
class SimpleDataClass:
    boolean: bool
    integer: int
    string: str
    timestamp: datetime.datetime


@dataclass
class NestedDataClass:
    plain: SimpleClass
    data: SimpleDataClass


class CompositeClass:
    ignore = decimal.Decimal

    data: SimpleDataClass
    inner: NestedDataClass
    identifier: uuid.UUID
    value: int


class TestTopological(unittest.TestCase):
    def assertOrder(self, order: List[T], first: T, second: T) -> None:
        self.assertIn(first, order)
        self.assertIn(second, order)
        self.assertLess(order.index(first), order.index(second))

    def test_simple(self) -> None:
        graph: Dict[int, Set[int]] = {
            0: set(),
            1: set(),
            2: set([3]),
            3: set([1]),
            4: set([0, 1]),
            5: set([0, 2]),
        }
        order = topological_sort(graph)
        self.assertEqual(order, [0, 1, 3, 2, 4, 5])

    def test_loop(self) -> None:
        graph: Dict[int, Set[int]] = {0: set([0])}
        order = topological_sort(graph)
        self.assertEqual(order, [0])

    def test_cycle(self) -> None:
        graph: Dict[int, Set[int]] = {
            0: set([1, 2]),
            1: set([2]),
            2: set([0, 3]),
            3: set(),
        }
        with self.assertRaises(RuntimeError):
            topological_sort(graph)

    def test_types(self) -> None:
        order = type_topological_sort([CompositeClass])
        self.assertNotIn(decimal.Decimal, order)
        self.assertOrder(order, bool, SimpleDataClass)
        self.assertOrder(order, int, SimpleDataClass)
        self.assertOrder(order, str, SimpleDataClass)
        self.assertOrder(order, datetime.datetime, SimpleDataClass)
        self.assertOrder(order, SimpleClass, NestedDataClass)
        self.assertOrder(order, SimpleDataClass, NestedDataClass)
        self.assertOrder(order, int, CompositeClass)
        self.assertOrder(order, uuid.UUID, CompositeClass)
        self.assertOrder(order, SimpleDataClass, CompositeClass)
        self.assertOrder(order, NestedDataClass, CompositeClass)

    def test_types_with_dependencies(self) -> None:
        order = type_topological_sort([NestedDataClass])
        self.assertNotIn(decimal.Decimal, order)

        fn = lambda cls: [decimal.Decimal] if is_dataclass_type(cls) else []
        order = type_topological_sort([NestedDataClass], fn)
        self.assertOrder(order, decimal.Decimal, SimpleDataClass)
        self.assertOrder(order, decimal.Decimal, NestedDataClass)


if __name__ == "__main__":
    unittest.main()
