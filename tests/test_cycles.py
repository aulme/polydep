from polydep.cycles import find_cycles, format_cycle

# --- find_cycles ---


def test_find_cycles_empty_for_acyclic_graph() -> None:
    edges = [("a", "b"), ("b", "c")]

    assert find_cycles(edges) == []


def test_find_cycles_detects_two_node_cycle() -> None:
    edges = [("a", "b"), ("b", "a")]

    assert find_cycles(edges) == [["a", "b"]]


def test_find_cycles_detects_transitive_cycle() -> None:
    edges = [("a", "b"), ("b", "c"), ("c", "a")]

    assert find_cycles(edges) == [["a", "b", "c"]]


def test_find_cycles_detects_self_loop() -> None:
    edges = [("a", "a")]

    assert find_cycles(edges) == [["a"]]


def test_find_cycles_deduplicates_same_cycle_from_different_starts() -> None:
    # The 3-node cycle is reachable starting from a, b, or c — report it once.
    edges = [("a", "b"), ("b", "c"), ("c", "a")]

    assert find_cycles(edges) == [["a", "b", "c"]]


def test_find_cycles_reports_multiple_independent_cycles_sorted() -> None:
    # alpha<->beta (length 2) and x->y->z->x (length 3); sorted by length then name.
    edges = [("alpha", "beta"), ("beta", "alpha"), ("x", "y"), ("y", "z"), ("z", "x")]

    assert find_cycles(edges) == [["alpha", "beta"], ["x", "y", "z"]]


# --- format_cycle ---


def test_format_cycle_closes_the_loop() -> None:
    assert format_cycle(["a", "b", "c"]) == "a -> b -> c -> a"


def test_format_cycle_self_loop() -> None:
    assert format_cycle(["a"]) == "a -> a"
