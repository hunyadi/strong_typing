import unittest

from strong_typing.slots import SlotsMeta


class MySlotBaseClass(metaclass=SlotsMeta):
    s: str
    b: bool
    i: int


class MySlotClass(MySlotBaseClass):
    o: str


class MyPlainClass:
    pass


class TestSerialization(unittest.TestCase):
    def test_slots(self) -> None:
        self.assertEqual(MySlotBaseClass.__dict__["__slots__"], ("s", "b", "i"))
        self.assertEqual(MySlotClass.__dict__["__slots__"], ("o",))

        p = MyPlainClass()
        p.c = 1  # type: ignore

        b = MySlotBaseClass()
        with self.assertRaises(AttributeError):
            b.c = 1  # type: ignore

        o = MySlotClass()
        with self.assertRaises(AttributeError):
            o.c = 1  # type: ignore


if __name__ == "__main__":
    unittest.main()
