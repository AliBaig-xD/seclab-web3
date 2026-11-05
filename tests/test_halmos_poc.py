from orchestrator.tools.halmos_poc import (extract_check_params, check_contract_of,
                                           build_halmos_poc, _ordered_values)

SRC = """pragma solidity ^0.8.20;
contract CheckMath {
    function add(uint256 a, uint256 b) internal pure returns (uint256) { unchecked { return a+b; } }
    function check_add_no_overflow(uint256 a, uint256 b) public pure { assert(add(a,b) >= a); }
}
"""


def test_extract_params():
    p = extract_check_params(SRC, "check_add_no_overflow")
    assert p == [("uint256", "a"), ("uint256", "b")]


def test_contract_of():
    assert check_contract_of(SRC, "check_add_no_overflow") == "CheckMath"


def test_ordered_values():
    assert _ordered_values({"a": 5, "b": 7}, [("uint256", "a"), ("uint256", "b")]) == [5, 7]
    assert _ordered_values({"a": 5}, [("uint256", "a"), ("uint256", "b")]) is None


def test_build_poc():
    poc = build_halmos_poc("CheckMath", "check_add_no_overflow", [5, 7], "./CheckMath.t.sol")
    assert "contract HalmosPoC is CheckMath" in poc
    assert "this.check_add_no_overflow(5, 7)" in poc
    assert "function test_counterexample() public" in poc
