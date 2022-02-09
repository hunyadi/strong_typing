import dataclasses
import inspect
import re
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class DocstringParam:
    name: str
    description: str


@dataclass
class DocstringReturns:
    description: str


@dataclass
class Docstring:
    long_description: Optional[str] = None
    short_description: Optional[str] = None
    params: Dict[str, DocstringParam] = dataclasses.field(default_factory=dict)
    returns: Optional[DocstringReturns] = None


def parse_type(type: type) -> Docstring:
    """
    Parse the docstring of a type into its components.

    :returns: Components of the documentation string.
    """

    return parse_text(type.__doc__)


def parse_text(text: str) -> Docstring:
    """
    Parse a ReST-style docstring into its components.

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

        if len(args) == 2:
            if args[0] == "param":
                params[args[1]] = DocstringParam(name=args[1], description=desc)

        elif len(args) == 1:
            if args[0] == "return" or args[0] == "returns":
                returns = DocstringReturns(description=desc)

    return Docstring(
        long_description=long_description,
        short_description=short_description,
        params=params,
        returns=returns,
    )
