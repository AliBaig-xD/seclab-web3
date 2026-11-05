from orchestrator.tools.autoinvariant import build_harness_contract

CI = {"contracts": [{"contract": "Vault", "state_vars": ["totalAssets", "totalShares"],
                     "functions": [{"name": "constructor", "sig": "constructor()"},
                                   {"name": "totalAssets", "vis": "public", "payable": False}]}]}


def test_build_harness_inherits_and_asserts():
    src, props = build_harness_contract(CI, "Vault",
        ["totalAssets stays solvent vs totalShares"], "../src/Vault.sol")
    assert src and "contract InvariantHarness is Vault" in src
    assert 'import "../src/Vault.sol";' in src
    assert "function echidna_" in src and len(props) >= 1


def test_build_harness_skips_constructor_args():
    ci = {"contracts": [{"contract": "V", "state_vars": ["a", "b"],
                         "functions": [{"name": "constructor", "sig": "constructor(address)"}]}]}
    src, props = build_harness_contract(ci, "V", ["a == b"], "../src/V.sol")
    assert src is None and props == []


def test_build_harness_none_when_no_invariants():
    src, props = build_harness_contract(CI, "Vault", ["unrelated text"], "../src/Vault.sol")
    assert src is None
