import sys
import unittest
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
)

from strong_typing.auxiliary import Alias, Annotated, float32, int32
from strong_typing.mapping import python_field_to_json_property
from strong_typing.name import TypeFormatter, python_type_to_name, python_type_to_str

T = TypeVar("T")


class SampleClass:
    pass


class DerivedClass(SampleClass):
    pass


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
            python_type_to_name(Dict[str, int], force=True),
            "Dict__str__int",
        )
        self.assertEqual(
            python_type_to_name(List[int], force=True),
            "List__int",
        )
        self.assertEqual(
            python_type_to_name(Set[int], force=True),
            "Set__int",
        )
        self.assertEqual(
            python_type_to_name(Type[str], force=True),
            "Type__str",
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

        self.assertEqual(python_type_to_name(T), "T")
        self.assertEqual(python_type_to_str(T), "T")

    def test_alias(self) -> None:
        self.assertEqual(python_field_to_json_property("id"), "id")
        self.assertEqual(
            python_field_to_json_property("id", Annotated[str, Alias("alias")]), "alias"
        )

    def test_special(self) -> None:
        self.assertEqual(python_type_to_str(None), "None")
        self.assertEqual(python_type_to_str(type(None)), "None")
        self.assertEqual(python_type_to_str(...), "...")
        self.assertEqual(python_type_to_str(type(...)), "...")
        self.assertEqual(python_type_to_str(Any), "Any")

    def test_callable(self) -> None:
        self.assertEqual(python_type_to_str(Callable[[], None]), "Callable[[], None]")
        self.assertEqual(
            python_type_to_str(Callable[[str], None]), "Callable[[str], None]"
        )
        self.assertEqual(
            python_type_to_str(Callable[[int], str]), "Callable[[int], str]"
        )
        self.assertEqual(
            python_type_to_str(Callable[[bool, int, str], None]),
            "Callable[[bool, int, str], None]",
        )

    def test_union(self) -> None:
        fmt = TypeFormatter(use_union_operator=True)
        self.assertEqual(fmt.python_type_to_str(Optional[str]), "str | None")
        self.assertEqual(fmt.python_type_to_str(Union[str, int]), "str | int")
        self.assertEqual(
            fmt.python_type_to_str(Union[str, int, None]), "str | int | None"
        )
        self.assertEqual(
            fmt.python_type_to_str(Union[None, str, int]), "None | str | int"
        )
        self.assertEqual(
            fmt.python_type_to_str(Optional["SampleClass"]), "SampleClass | None"
        )
        self.assertEqual(
            fmt.python_type_to_str(Union["SampleClass", "DerivedClass", None]),
            "SampleClass | DerivedClass | None",
        )

        self.assertEqual(python_type_to_str(Optional[str]), "Optional[str]")
        self.assertEqual(python_type_to_str(Union[str, int]), "Union[str, int]")
        self.assertEqual(
            python_type_to_str(Union[str, int, None]), "Union[str, int, None]"
        )
        self.assertEqual(
            python_type_to_str(Union[None, str, int]), "Union[None, str, int]"
        )
        self.assertEqual(
            python_type_to_str(Optional["SampleClass"]), "Optional[SampleClass]"
        )
        self.assertEqual(
            python_type_to_str(Union["SampleClass", "DerivedClass", None]),
            "Union[SampleClass, DerivedClass, None]",
        )

    def test_auxiliary(self) -> None:
        self.assertEqual(python_type_to_str(float32), "float32")
        self.assertEqual(python_type_to_str(int32), "int32")

        fmt = TypeFormatter(use_union_operator=True)
        self.assertEqual(fmt.python_type_to_str(Optional[float32]), "float32 | None")
        self.assertEqual(fmt.python_type_to_str(Optional[int32]), "int32 | None")

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

    def test_transform(self) -> None:
        fmt = TypeFormatter(
            context=sys.modules[self.__module__],
            type_transform=lambda typ: f"*{typ.__name__}*",
            use_union_operator=True,
        )
        self.assertEqual(fmt.python_type_to_str(Optional[str]), "*str* | None")
        self.assertEqual(fmt.python_type_to_str(Union[str, int]), "*str* | *int*")
        self.assertEqual(
            fmt.python_type_to_str(Union[str, int, None]), "*str* | *int* | None"
        )
        self.assertEqual(
            fmt.python_type_to_str(Union[None, str, int]), "None | *str* | *int*"
        )
        self.assertEqual(
            fmt.python_type_to_str(Optional["SampleClass"]), "*SampleClass* | None"
        )
        self.assertEqual(
            fmt.python_type_to_str(Union["SampleClass", "DerivedClass", None]),
            "*SampleClass* | *DerivedClass* | None",
        )

    def test_literal(self) -> None:
        self.assertEqual(
            python_type_to_str(
                Literal[
                    False,
                    2,
                    "string",
                ]
            ),
            "Literal[False, 2, 'string']",
        )

        fmt = TypeFormatter(
            context=sys.modules[self.__module__],
            value_transform=lambda value: f"`{value}`",
            use_union_operator=True,
        )
        self.assertEqual(
            fmt.python_type_to_str(
                Literal[
                    False,
                    2,
                    "string",
                ]
            ),
            "Literal[`False`, `2`, `string`]",
        )

    def test_illegal(self) -> None:
        with self.assertRaises(ValueError):
            python_type_to_str(False)
        with self.assertRaises(ValueError):
            python_type_to_str(23)


if __name__ == "__main__":
    unittest.main()
