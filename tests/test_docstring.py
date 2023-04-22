import enum
import inspect
import sys
import typing
import unittest
from dataclasses import dataclass
from typing import Optional, TypeVar

from test_sample_exceptions import CustomException

from strong_typing.docstring import has_default_docstring, has_docstring, parse_type

T = TypeVar("T")


def required(obj: Optional[T]) -> T:
    "Casts an optional type to a required type."

    return typing.cast(T, obj)


class NoDescriptionClass:
    pass


@dataclass
class NoDescriptionDataclass:
    pass


class NoDescriptionEnumeration(enum.Enum):
    pass


class ShortDescriptionClass:
    "Short description."


class MultiLineShortDescriptionClass:
    """
    A short description that
    spans multiple lines.
    """


class MultiLineLongDescriptionClass:
    """
    Short description.

    A description text that
    spans multiple lines.
    """


@dataclass
class ShortDescriptionParameterClass:
    """
    Short description.

    :param a: Short description for `a`.
    """

    a: int


@dataclass
class MultiLineDescriptionParametersClass:
    """
    Short description.

    A description text that
    spans multiple lines.

    :param a: Short description for `a`.
    :param b2: Long description for `b` that
    spans multiple lines.
    :param c_3: Description for `c`.
    :see: https://example.com
    """

    a: int
    b2: str
    c_3: float


@dataclass
class MissingMemberClass:
    """
    Short description.

    :param a: Short description for `a`.
    """


class SampleClass:
    def instance_method(self, a: str, b: Optional[int]) -> str:
        """
        Short description of an instance method.

        :param a: Short description for `a`.
        :param b: Short description for `b`.
        :return: A return value.
        :raise TypeError: A type exception rarely raised.
        :raise ValueError: A value exception rarely raised.
        :raise CustomException: A custom exception.
        """
        return ""

    def other_instance_method(self, a: str, b: Optional[int]) -> str:
        """
        Short description of an instance method.

        :param a: Short description for `a`.
        :param b: Short description for `b`.
        :returns: A return value.
        :raises TypeError: A type exception rarely raised.
        :raises ValueError: A value exception rarely raised.
        :raises CustomException: A custom exception.
        """
        return ""

    @classmethod
    def class_method(cls, a: str) -> str:
        """
        Short description of a class method.

        :param a: Short description for `a`.
        :returns: A return value.
        """
        return ""

    @staticmethod
    def static_method(a: str) -> None:
        """
        Short description of a static method.

        :param a: Short description for `a`.
        """
        pass

    def no_type_annotation_method(self):  # type: ignore
        """
        Short description of an instance method without parameter or return value annotation.

        :returns: A return value.
        """
        pass


class TestDocstring(unittest.TestCase):
    def test_default_docstring(self) -> None:
        self.assertFalse(has_default_docstring(NoDescriptionClass))
        self.assertTrue(has_default_docstring(NoDescriptionDataclass))
        self.assertFalse(has_default_docstring(ShortDescriptionClass))
        if sys.version_info >= (3, 11):
            self.assertFalse(has_default_docstring(NoDescriptionEnumeration))
        else:
            self.assertTrue(has_default_docstring(NoDescriptionEnumeration))

    def test_any_docstring(self) -> None:
        self.assertFalse(has_docstring(NoDescriptionClass))
        self.assertFalse(has_docstring(NoDescriptionDataclass))
        self.assertFalse(has_docstring(NoDescriptionEnumeration))
        self.assertTrue(has_docstring(ShortDescriptionClass))

    def test_no_description(self) -> None:
        docstring = parse_type(NoDescriptionClass)
        self.assertIsNone(docstring.short_description)
        self.assertIsNone(docstring.long_description)
        self.assertFalse(docstring.params)
        self.assertIsNone(docstring.returns)
        self.assertEqual(str(docstring), "")

    def test_short_description(self) -> None:
        docstring = parse_type(ShortDescriptionClass)
        self.assertEqual(docstring.short_description, "Short description.")
        self.assertIsNone(docstring.long_description)
        self.assertEqual(str(docstring), ShortDescriptionClass.__doc__)

    def test_multi_line_description(self) -> None:
        docstring = parse_type(MultiLineShortDescriptionClass)
        self.assertEqual(
            docstring.short_description,
            "A short description that spans multiple lines.",
        )
        self.assertIsNone(docstring.long_description)
        self.assertEqual(
            str(docstring), "A short description that spans multiple lines."
        )

        docstring = parse_type(MultiLineLongDescriptionClass)
        self.assertEqual(docstring.short_description, "Short description.")
        self.assertEqual(
            docstring.long_description, "A description text that\nspans multiple lines."
        )
        self.assertEqual(
            str(docstring),
            "Short description.\n\nA description text that\nspans multiple lines.",
        )

    def test_dataclass_parameter_list(self) -> None:
        docstring = parse_type(ShortDescriptionParameterClass)
        self.assertEqual(docstring.short_description, "Short description.")
        self.assertIsNone(docstring.long_description)
        self.assertEqual(len(docstring.params), 1)
        self.assertEqual(
            docstring.params["a"].description, "Short description for `a`."
        )
        self.assertEqual(
            str(docstring),
            inspect.cleandoc(ShortDescriptionParameterClass.__doc__ or ""),
        )

        docstring = parse_type(MultiLineDescriptionParametersClass)
        self.assertEqual(docstring.short_description, "Short description.")
        self.assertEqual(
            docstring.long_description, "A description text that\nspans multiple lines."
        )
        self.assertEqual(len(docstring.params), 3)
        self.assertEqual(
            docstring.params["a"].description,
            "Short description for `a`.",
        )
        self.assertEqual(docstring.params["a"].param_type, int)
        self.assertEqual(
            docstring.params["b2"].description,
            "Long description for `b` that spans multiple lines.",
        )
        self.assertEqual(docstring.params["b2"].param_type, str)
        self.assertEqual(docstring.params["c_3"].description, "Description for `c`.")
        self.assertEqual(docstring.params["c_3"].param_type, float)
        self.assertEqual(
            str(docstring),
            "\n".join(
                [
                    "Short description.",
                    "",
                    "A description text that",
                    "spans multiple lines.",
                    "",
                    ":param a: Short description for `a`.",
                    ":param b2: Long description for `b` that spans multiple lines.",
                    ":param c_3: Description for `c`.",
                ]
            ),
        )

        with self.assertRaises(TypeError):
            parse_type(MissingMemberClass)

    def test_function_parameter_list(self) -> None:
        docstring = parse_type(SampleClass.instance_method)
        self.assertEqual(
            docstring.short_description, "Short description of an instance method."
        )
        self.assertIsNone(docstring.long_description)
        self.assertEqual(len(docstring.params), 2)
        self.assertEqual(
            docstring.params["a"].description, "Short description for `a`."
        )
        self.assertEqual(
            docstring.params["b"].description, "Short description for `b`."
        )
        self.assertIsNotNone(docstring.returns)
        self.assertEqual(required(docstring.returns).description, "A return value.")

        self.assertEqual(len(docstring.raises), 3)
        self.assertEqual(
            docstring.raises["TypeError"].description,
            "A type exception rarely raised.",
        )
        self.assertEqual(docstring.raises["TypeError"].raise_type, TypeError)
        self.assertEqual(
            docstring.raises["ValueError"].description,
            "A value exception rarely raised.",
        )
        self.assertEqual(docstring.raises["ValueError"].raise_type, ValueError)
        self.assertEqual(
            docstring.raises["CustomException"].description,
            "A custom exception.",
        )
        self.assertEqual(
            docstring.raises["CustomException"].raise_type, CustomException
        )

        docstring = parse_type(SampleClass.other_instance_method)
        self.assertEqual(
            str(docstring),
            inspect.cleandoc(SampleClass.other_instance_method.__doc__ or ""),
        )

        docstring = parse_type(SampleClass.class_method)
        self.assertEqual(
            docstring.short_description, "Short description of a class method."
        )
        self.assertIsNone(docstring.long_description)
        self.assertEqual(len(docstring.params), 1)
        self.assertEqual(
            docstring.params["a"].description, "Short description for `a`."
        )
        self.assertIsNotNone(docstring.returns)
        self.assertEqual(required(docstring.returns).description, "A return value.")
        self.assertEqual(
            str(docstring), inspect.cleandoc(SampleClass.class_method.__doc__ or "")
        )

        docstring = parse_type(SampleClass.static_method)
        self.assertEqual(
            docstring.short_description, "Short description of a static method."
        )
        self.assertIsNone(docstring.long_description)
        self.assertEqual(len(docstring.params), 1)
        self.assertEqual(
            docstring.params["a"].description, "Short description for `a`."
        )
        self.assertIsNone(docstring.returns)
        self.assertEqual(
            str(docstring), inspect.cleandoc(SampleClass.static_method.__doc__ or "")
        )

        with self.assertRaises(TypeError):
            parse_type(SampleClass.no_type_annotation_method)


if __name__ == "__main__":
    unittest.main()
