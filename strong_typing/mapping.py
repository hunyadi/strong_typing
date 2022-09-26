import keyword

from .auxiliary import Alias
from .inspection import get_annotation


def python_field_to_json_property(python_id: str, python_type: type = None) -> str:
    """
    Map a Python field identifier to a JSON property name.

    Authors may use an underscore appended at the end of a Python identifier as per PEP 8 if it clashes with a Python
    keyword: e.g. `in` would become `in_` and `from` would become `from_`. Remove these suffixes when exporting to JSON.

    Authors may supply an explicit alias with the type annotation `Alias`, e.g. `Annotated[MyType, Alias("alias")]`.
    """

    if python_type is not None:
        alias = get_annotation(python_type, Alias)
        if alias:
            return alias.name

    if python_id.endswith("_"):
        id = python_id[:-1]
        if keyword.iskeyword(id):
            return id

    return python_id
