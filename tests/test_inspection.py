import datetime
import unittest
from typing import Dict, List, Optional, Union

from strong_typing.inspection import get_referenced_types


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


if __name__ == "__main__":
    unittest.main()
