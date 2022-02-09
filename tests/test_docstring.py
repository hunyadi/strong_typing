import unittest
from dataclasses import dataclass
from typing import Optional

from strong_typing.docstring import parse_type


class NoDescriptionClass:
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


class SampleClass:
    def instance_method(self, a: str, b: Optional[int]) -> str:
        """
        Short description of an instance method.

        :param a: Short description for `a`.
        :param b: Short description for `b`.
        :return: A return value.
        """

    @classmethod
    def class_method(cls, a: str) -> str:
        """
        Short description of a class method.

        :param a: Short description for `a`.
        :returns: A return value.
        """

    @staticmethod
    def static_method(a: str) -> None:
        """
        Short description of a static method.

        :param a: Short description for `a`.
        """


class TestDocstring(unittest.TestCase):
    def test_no_description(self):
        docstring = parse_type(NoDescriptionClass)
        self.assertIsNone(docstring.short_description)
        self.assertIsNone(docstring.long_description)
        self.assertFalse(docstring.params)
        self.assertIsNone(docstring.returns)

    def test_short_description(self):
        docstring = parse_type(ShortDescriptionClass)
        self.assertEqual(docstring.short_description, "Short description.")
        self.assertIsNone(docstring.long_description)

    def test_multi_line_description(self):
        docstring = parse_type(MultiLineShortDescriptionClass)
        self.assertEqual(
            docstring.short_description,
            "A short description that spans multiple lines.",
        )
        self.assertIsNone(docstring.long_description)

        docstring = parse_type(MultiLineLongDescriptionClass)
        self.assertEqual(docstring.short_description, "Short description.")
        self.assertEqual(
            docstring.long_description, "A description text that\nspans multiple lines."
        )

    def test_dataclass_parameter_list(self):
        docstring = parse_type(ShortDescriptionParameterClass)
        self.assertEqual(docstring.short_description, "Short description.")
        self.assertIsNone(docstring.long_description)
        self.assertEqual(len(docstring.params), 1)
        self.assertEqual(
            docstring.params["a"].description, "Short description for `a`."
        )

        docstring = parse_type(MultiLineDescriptionParametersClass)
        self.assertEqual(docstring.short_description, "Short description.")
        self.assertEqual(
            docstring.long_description, "A description text that\nspans multiple lines."
        )
        self.assertEqual(len(docstring.params), 3)
        self.assertEqual(
            docstring.params["a"].description, "Short description for `a`."
        )
        self.assertEqual(
            docstring.params["b2"].description,
            "Long description for `b` that spans multiple lines.",
        )
        self.assertEqual(docstring.params["c_3"].description, "Description for `c`.")

    def test_function_parameter_list(self):
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
        self.assertEqual(docstring.returns.description, "A return value.")

        docstring = parse_type(SampleClass.class_method)
        self.assertEqual(
            docstring.short_description, "Short description of a class method."
        )
        self.assertIsNone(docstring.long_description)
        self.assertEqual(len(docstring.params), 1)
        self.assertEqual(
            docstring.params["a"].description, "Short description for `a`."
        )
        self.assertEqual(docstring.returns.description, "A return value.")

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


if __name__ == "__main__":
    unittest.main()
