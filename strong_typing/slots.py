from typing import Any, TypeVar

T = TypeVar("T")


class SlotsMeta(type):
    def __new__(cls: type[T], name: str, bases: tuple[type, ...], ns: dict[str, Any]) -> T:
        # caller may have already provided slots, in which case just retain them and keep going
        slots: tuple[str, ...] = ns.get("__slots__", ())

        # add fields with type annotations to slots
        annotations: dict[str, Any] = ns.get("__annotations__", {})
        members = tuple(member for member in annotations.keys() if member not in slots)

        # assign slots
        ns["__slots__"] = slots + tuple(members)
        return super().__new__(cls, name, bases, ns)  # type: ignore


class Slots(metaclass=SlotsMeta):
    pass
