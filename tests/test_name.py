import unittest
from typing import Dict, List, Optional, Union

from strong_typing.auxiliary import Alias, Annotated
from strong_typing.name import python_type_to_name
from strong_typing.serialization import python_id_to_json_field


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
        self.assertEqual(
            python_type_to_name(Union[str, int, None], force=True),
            "Union__str__int__NoneType",
        )

    def test_alias(self):
        self.assertEqual(python_id_to_json_field("id"), "id")
        self.assertEqual(
            python_id_to_json_field("id", Annotated[str, Alias("alias")]), "alias"
        )


if __name__ == "__main__":
    unittest.main()
