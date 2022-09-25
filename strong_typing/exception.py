class JsonKeyError(Exception):
    "Raised when deserialization for a class or union type has failed because a matching member was not found."


class JsonValueError(Exception):
    "Raised when (de)serialization of data has failed due to invalid value."


class JsonTypeError(Exception):
    "Raised when deserialization of data has failed due to a type mismatch."
