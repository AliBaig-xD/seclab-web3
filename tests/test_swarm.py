from orchestrator.swarm import (extract_function, contract_preamble, slice_source,
                                protocol_header, SwarmEngine)

SRC = """// SPDX
pragma solidity ^0.8.20;
contract Vault {
    mapping(address => uint256) public balances;
    uint256 public total;
    function deposit() external payable { balances[msg.sender] += msg.value; total += msg.value; }
    function withdraw() external {
        uint256 b = balances[msg.sender];
        (bool ok, ) = msg.sender.call{value: b}("");
        balances[msg.sender] = 0;
    }
}
"""
ARRAY = '[{"vuln_type":"reentrancy","location":"Vault.sol:7","precondition":"call before zero","claimed_impact":"drain","rationale":"r"}]'


class FakeClient:
    def __init__(self): self.calls = 0
    def generate(self, prompt, system=None):
        self.calls += 1
        return ARRAY


def test_extract_function_brace_matched():
    f = extract_function(SRC, "withdraw")
    assert f and f.startswith("function withdraw()") and f.rstrip().endswith("}")
    assert "balances[msg.sender] = 0;" in f


def test_extract_missing_function():
    assert extract_function(SRC, "nope") is None


def test_contract_preamble_has_state():
    pre = contract_preamble(SRC, "Vault")
    assert "balances" in pre and "total" in pre


def test_slice_source_includes_members():
    s = slice_source(SRC, "Vault", ["Vault.withdraw"])
    assert "withdraw" in s and "balances" in s


def test_protocol_header():
    h = protocol_header({"roles": ["owner"], "invariants": ["sum==total"], "assumptions": []})
    assert "owner" in h and "sum==total" in h
    assert "no protocol model" in protocol_header(None)


SLICES = [{"id": "Vault.withdraw", "contract": "Vault", "entry": "withdraw",
           "functions": ["Vault.withdraw"], "state": ["balances"], "roles": [],
           "privileged": False, "payable": False, "low_level": True}]
PAIRS = [(("Vault", "deposit"), ("Vault", "withdraw"), ["balances"])]


def test_swarm_map_and_reduce():
    c = FakeClient()
    eng = SwarmEngine(c, concurrency=1, deep=True, max_pairs=4)
    hs = eng.run(SLICES, PAIRS, {"Vault": SRC}, {"roles": ["owner"], "invariants": ["x"]})
    assert len(hs) >= 2                     # slice pass (+deep) and a cross-slice hypothesis
    assert eng.stats["slices"] == 1
    assert eng.stats["deep"] == 1           # low_level slice deepened
    assert eng.stats["pairs"] == 1
    assert any("cross-slice" in (h.rationale or "") for h in hs)
    assert any("slice Vault.withdraw" in (h.rationale or "") for h in hs)


def test_swarm_skips_pair_with_missing_source():
    eng = SwarmEngine(FakeClient(), max_pairs=4)
    out = eng.consolidate([(("X", "a"), ("Y", "b"), ["s"])], {}, "hdr", {})
    assert out == []
