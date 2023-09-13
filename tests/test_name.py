import unittest
from typing import Dict, List, Optional, Union

from strong_typing.auxiliary import Alias, Annotated, float32, int32
from strong_typing.mapping import python_field_to_json_property
from strong_typing.name import python_type_to_name, python_type_to_str


class TestName(unittest.TestCase):
    def test_builtin(self) -> None:
        self.assertEqual(python_type_to_name(type(None)), "NoneType")
        self.assertEqual(python_type_to_name(int), "int")
        self.assertEqual(python_type_to_name(str), "str")

    def test_generic(self) -> None:
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

        with self.assertRaises(TypeError):
            python_type_to_name(Optional[str])
        with self.assertRaises(TypeError):
            python_type_to_name(List[int])
        with self.assertRaises(TypeError):
            python_type_to_name(Dict[str, int])
        with self.assertRaises(TypeError):
            python_type_to_name(Union[str, int, None])

    def test_alias(self) -> None:
        self.assertEqual(python_field_to_json_property("id"), "id")
        self.assertEqual(
            python_field_to_json_property("id", Annotated[str, Alias("alias")]), "alias"
        )

    def test_auxiliary(self) -> None:
        self.assertEqual(python_type_to_str(float32), "float32")
        self.assertEqual(python_type_to_str(int32), "int32")
        self.assertEqual(python_type_to_str(Optional[float32]), "Optional[float32]")
        self.assertEqual(python_type_to_str(Optional[int32]), "Optional[int32]")
        self.assertEqual(
            python_type_to_str(Annotated[float32, Alias("float")]),
            "Annotated[float32, Alias('float')]",
        )
        self.assertEqual(
            python_type_to_str(Annotated[int32, Alias("int")]),
            "Annotated[int32, Alias('int')]",
        )


if __name__ == "__main__":
    unittest.main()
