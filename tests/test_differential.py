from orchestrator.tools.differential import diff_results


def test_diff_results():
    a = {"test_a()": True, "test_b()": True, "test_only_a()": True}
    b = {"test_a()": True, "test_b()": False, "test_only_b()": True}
    d = diff_results(a, b)
    assert d == ["test_b()"]                     # only the shared+divergent one


def test_diff_results_identical():
    r = {"t()": True}
    assert diff_results(r, r) == []
