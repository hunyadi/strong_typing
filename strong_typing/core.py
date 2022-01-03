from typing import (
    Dict,
    List,
    Union,
)


class JsonObject:
    "Placeholder type for an unrestricted JSON object."


class JsonArray:
    "Placeholder type for an unrestricted JSON array."


JsonType = Union[None, bool, int, float, str, Dict[str, "JsonType"], List["JsonType"]]
Schema = JsonType
