from typing import Callable, Dict, Iterable, List, Set, TypeVar

from .inspection import get_class_properties, get_referenced_types

T = TypeVar("T")


def topological_sort(graph: Dict[T, Set[T]]) -> List[T]:
    """
    Performs a topological sort of a graph.

    Nodes with no outgoing edges are first. Nodes with no incoming edges are last.
    The topological ordering is not unique.

    :param graph: A dictionary of mappings from nodes to adjacent nodes. Keys and set members must be hashable.
    :returns: The list of nodes in topological order.
    """

    # empty list that will contain the sorted nodes (in reverse order)
    ordered: List[T] = []

    seen: Dict[T, bool] = {}

    def _visit(n):
        status = seen.get(n)
        if status is not None:
            if status:  # node has a permanent mark
                return
            else:  # node has a temporary mark
                raise RuntimeError(f"cycle detected in graph for node {n}")

        seen[n] = False  # apply temporary mark
        for m in graph[n]:  # visit all adjacent nodes
            if m != n:  # ignore self-referencing nodes
                _visit(m)

        seen[n] = True  # apply permanent mark
        ordered.append(n)

    for n in graph.keys():
        _visit(n)

    return ordered


def type_topological_sort(
    types: Iterable[type], dependency_fn: Callable[[type], Iterable[type]] = None
) -> List[type]:
    """
    Performs a topological sort of a list of types.

    Types that don't depend on other types (i.e. fundamental types) are first. Types on which no other types depend
    are last. The topological ordering is not unique.

    :param types: A list of types (simple or composite).
    :param dependency_fn: Returns a list of additional dependencies for a class (e.g. classes referenced by a foreign key).
    :returns: The list of types in topological order.
    """

    if not all(isinstance(typ, type) for typ in types):
        raise TypeError("expected a list of types")

    graph: Dict[type, Set[type]] = {}

    queue = list(types)
    while queue:
        cls = queue.pop()

        references: Set[type] = set()
        graph[cls] = references
        for _, typ in get_class_properties(cls):
            for arg in get_referenced_types(typ):
                if arg not in graph:
                    queue.append(arg)
                references.add(arg)

        if dependency_fn:
            for typ in dependency_fn(cls):
                if typ not in graph:
                    queue.append(typ)
                references.add(typ)

    return topological_sort(graph)
