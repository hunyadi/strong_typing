import unittest
from typing import Dict, List, Optional

from strong_typing.name import python_type_to_name


class TestName(unittest.TestCase):
    def test_builtin(self):
        self.assertEqual(python_type_to_name(type(None)), "NoneType")
        self.assertEqual(python_type_to_name(int), "int")
        self.assertEqual(python_type_to_name(str), "str")

    def test_generic(self):
        self.assertEqual(
            python_type_to_name(Optional[str], force=True),
            "Optional__str",
        )
        self.assertEqual(
            python_type_to_name(List[int], force=True),
            "List__int",
        )
        self.assertEqual(
            python_type_to_name(Dict[str, int], force=True),
            "Dict__str__int",
        )


if __name__ == "__main__":
    unittest.main()
