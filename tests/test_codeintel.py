from orchestrator.codeintel import (call_graph, entrypoints, reachable, interaction_pairs,
                                    build_slices, is_privileged)

MODEL = {"contracts": [{
    "contract": "Vault", "inherits": [], "state_vars": ["balances", "paused"],
    "functions": [
        {"name": "deposit", "sig": "deposit()", "vis": "external", "modifiers": [],
         "reads": ["balances"], "writes": ["balances"], "calls": [], "external_calls": [],
         "payable": True, "low_level": False},
        {"name": "withdraw", "sig": "withdraw()", "vis": "external", "modifiers": [],
         "reads": ["balances"], "writes": ["balances"], "calls": ["_pay"], "external_calls": [],
         "payable": False, "low_level": True},
        {"name": "_pay", "sig": "_pay()", "vis": "internal", "modifiers": [],
         "reads": [], "writes": [], "calls": [], "external_calls": [], "payable": False,
         "low_level": True},
        {"name": "pause", "sig": "pause()", "vis": "external", "modifiers": ["onlyOwner"],
         "reads": [], "writes": ["paused"], "calls": [], "external_calls": [],
         "payable": False, "low_level": False},
    ]}]}


def test_call_graph_and_reachability():
    g = call_graph(MODEL)
    assert g[("Vault", "withdraw")] == [("Vault", "_pay")]
    assert ("Vault", "_pay") in reachable(g, ("Vault", "withdraw"))


def test_entrypoints_excludes_internal():
    eps = entrypoints(MODEL)
    assert ("Vault", "withdraw") in eps and ("Vault", "_pay") not in eps


def test_privileged_detection():
    pause = MODEL["contracts"][0]["functions"][3]
    assert is_privileged(pause) is True
    assert is_privileged(MODEL["contracts"][0]["functions"][0]) is False


def test_interaction_pairs_find_shared_state():
    pairs = interaction_pairs(MODEL)
    shared = {(a[1], b[1]): s for a, b, s in pairs}
    assert ("deposit", "withdraw") in shared
    assert shared[("deposit", "withdraw")] == ["balances"]
    # pause writes `paused` which nobody reads -> no pair from it
    assert not any(a[1] == "pause" for a, _b, _s in pairs)


def test_build_slices():
    sl = {s["id"]: s for s in build_slices(MODEL)}
    assert "Vault.withdraw" in sl
    w = sl["Vault.withdraw"]
    assert "Vault._pay" in w["functions"]       # transitive callee included
    assert "balances" in w["state"]
    assert sl["Vault.pause"]["privileged"] is True
