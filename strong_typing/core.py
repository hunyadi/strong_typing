from typing import (
    Dict,
    List,
    Union,
)

JsonType = Union[None, bool, int, float, str, Dict[str, "JsonType"], List["JsonType"]]
Schema = JsonType
