import dataclasses
import inspect
import re
from dataclasses import dataclass
from typing import Dict, Optional

from .inspection import is_dataclass_type


@dataclass
class DocstringParam:
    """
    A parameter declaration in a parameter block.

    :param name: The name of the parameter.
    :param description: The description text for the parameter.
    """

    name: str
    description: str


@dataclass
class DocstringReturns:
    """
    A returns declaration extracted from a docstring.

    :param description: The description text for the return value.
    """

    description: str


@dataclass
class Docstring:
    """
    Represents the documentation string (a.k.a. docstring) for a type such as a (data) class or function.

    A docstring is broken down into the following components:
    * A short description, which is the first block of text in the documentation string, and ends with a double
      newline or a parameter block.
    * A long description, which is the optional block of text following the short description, and ends with
      a parameter block.
    * A parameter block of named parameter and description string pairs in ReST-style.
    * A returns declaration, which adds explanation to the return value.

    When the docstring is attached to a data class, it is understood as the documentation string of the class
    `__init__` method.

    :param short_description: The short description text parsed from a docstring.
    :param long_description: The long description text parsed from a docstring.
    :param params: The parameter block extracted from a docstring.
    :param returns: The returns declaration extracted from a docstring.
    """

    short_description: Optional[str] = None
    long_description: Optional[str] = None
    params: Dict[str, DocstringParam] = dataclasses.field(default_factory=dict)
    returns: Optional[DocstringReturns] = None

    @property
    def full_description(self) -> Optional[str]:
        if self.short_description and self.long_description:
            return f"{self.short_description}\n\n{self.long_description}"
        elif self.short_description:
            return self.short_description
        else:
            return None


def parse_type(typ: type) -> Docstring:
    """
    Parse the docstring of a type into its components.

    :param typ: The type whose documentation string to parse.
    :returns: Components of the documentation string.
    """

    if has_docstring(typ):
        return parse_text(typ.__doc__)  # type: ignore
    else:
        return Docstring()


def parse_text(text: str) -> Docstring:
    """
    Parse a ReST-style docstring into its components.

    :param text: The documentation string to parse, typically acquired as `type.__doc__`.
    :returns: Components of the documentation string.
    """

    if not text:
        return Docstring()

    # find block that starts object metadata block (e.g. `:param p:` or `:returns:`)
    text = inspect.cleandoc(text)
    match = re.search("^:", text, flags=re.MULTILINE)
    if match:
        desc_chunk = text[: match.start()]
        meta_chunk = text[match.start() :]
    else:
        desc_chunk = text
        meta_chunk = ""

    # split description text into short and long description
    parts = desc_chunk.split("\n\n", 1)

    # ensure short description has no newlines
    short_description = parts[0].strip().replace("\n", " ") or None

    # ensure long description preserves its structure (e.g. preformatted text)
    if len(parts) > 1:
        long_description = parts[1].strip() or None
    else:
        long_description = None

    params: Dict[str, DocstringParam] = {}
    returns = None
    for match in re.finditer(
        r"(^:.*?)(?=^:|\Z)", meta_chunk, flags=re.DOTALL | re.MULTILINE
    ):
        chunk = match.group(0)
        if not chunk:
            continue

        args_chunk, desc_chunk = chunk.lstrip(":").split(":", 1)
        args = args_chunk.split()
        desc = desc_chunk.strip().replace("\n", " ")

        if len(args) > 0:
            kw = args[0]
            if len(args) == 2:
                if kw == "param":
                    params[args[1]] = DocstringParam(name=args[1], description=desc)

            elif len(args) == 1:
                if kw == "return" or kw == "returns":
                    returns = DocstringReturns(description=desc)

    return Docstring(
        long_description=long_description,
        short_description=short_description,
        params=params,
        returns=returns,
    )


def has_default_docstring(typ: type) -> bool:
    "Check if class has the auto-generated string assigned by @dataclass."

    return (
        is_dataclass_type(typ)
        and typ.__doc__ is not None
        and re.match(f"^{re.escape(typ.__name__)}[(].*[)]$", typ.__doc__) is not None
    )


def has_docstring(typ: type) -> bool:
    "Check if class has a documentation string other than the auto-generated string assigned by @dataclass."

    if has_default_docstring(typ):
        return False

    return bool(typ.__doc__)
