from orchestrator.invariants import _public_getters, echidna_property, synthesize_echidna, halmos_check

CI = {"contracts": [{"contract": "Vault", "state_vars": ["totalAssets", "totalShares"],
                     "functions": [{"name": "previewRedeem", "vis": "public", "payable": False},
                                   {"name": "deposit", "vis": "external", "payable": True}]}]}


def test_public_getters():
    g = _public_getters(CI, "Vault")
    assert "totalAssets" in g and "totalShares" in g and "previewRedeem" in g
    assert "deposit" not in g   # payable excluded


def test_echidna_property_stub():
    p = echidna_property("Vault", "no-insolvency", "totalAssets() >= totalShares()")
    assert "function echidna_no_insolvency() public view returns (bool)" in p
    assert "return totalAssets() >= totalShares();" in p


def test_synthesize_from_invariants():
    inv = ["totalAssets must stay solvent vs totalShares", "previewRedeem bounded"]
    out = synthesize_echidna(CI, "Vault", inv)
    # first invariant references two getters -> a relational property
    assert any("totalAssets()" in v and "totalShares()" in v for v in out.values())


def test_halmos_check_stub():
    c = halmos_check("add-no-overflow", "add", ["uint256", "uint256"], "a0 + a1 >= a0")
    assert "function check_add_no_overflow(uint256 a0, uint256 a1) public" in c
    assert "assert(a0 + a1 >= a0);" in c
