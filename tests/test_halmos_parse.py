from orchestrator.tools.halmos import parse_halmos_json

SAMPLE = {"test_results": {"test/CheckMath.t.sol:CheckMath": [
    {"name": "check_add_commutes(uint256,uint256)", "exitcode": 0, "num_models": 0, "models": []},
    {"name": "check_add_no_overflow(uint256,uint256)", "exitcode": 1, "num_models": 1,
     "models": [{"model": {"p_b": {"variable_name": "b", "value": 18014398509481977},
                           "p_a": {"variable_name": "a", "value": 123}}}]},
]}}


def test_parse_halmos():
    r = parse_halmos_json(SAMPLE)
    assert r["check_add_commutes"]["failed"] is False
    assert r["check_add_no_overflow"]["failed"] is True
    assert r["check_add_no_overflow"]["counterexample"]["b"] == 18014398509481977


def test_parse_halmos_empty():
    assert parse_halmos_json({}) == {}
