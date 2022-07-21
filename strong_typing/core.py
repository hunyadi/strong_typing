from typing import Dict, List, Union


class JsonObject:
    "Placeholder type for an unrestricted JSON object."


class JsonArray:
    "Placeholder type for an unrestricted JSON array."


# a JSON type with possible `null` values
JsonType = Union[  # type: ignore
    None,
    bool,
    int,
    float,
    str,
    Dict[str, "JsonType"],  # type: ignore
    List["JsonType"],  # type: ignore
]

# a JSON type that cannot contain `null` values
StrictJsonType = Union[  # type: ignore
    bool,
    int,
    float,
    str,
    Dict[str, "StrictJsonType"],  # type: ignore
    List["StrictJsonType"],  # type: ignore
]

# a meta-type that captures the object type in a JSON schema
Schema = Dict[str, "StrictJsonType"]  # type: ignore
