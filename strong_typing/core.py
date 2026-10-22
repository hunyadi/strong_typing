"""
Type-safe data interchange for Python data classes.

:see: https://github.com/hunyadi/strong_typing
"""


class JsonObject:
    "Placeholder type for an unrestricted JSON object."


class JsonArray:
    "Placeholder type for an unrestricted JSON array."


# a JSON type with possible `null` values
JsonType = None | bool | int | float | str | dict[str, "JsonType"] | list["JsonType"]

# a JSON type that cannot contain `null` values
StrictJsonType = bool | int | float | str | dict[str, "StrictJsonType"] | list["StrictJsonType"]

# a meta-type that captures the object type in a JSON schema
Schema = dict[str, JsonType]
