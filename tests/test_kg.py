from orchestrator.kg import KnowledgeGraph

MODEL = {"contracts": [{
    "contract": "Vault", "inherits": ["Ownable"], "state_vars": ["balances", "paused"],
    "functions": [
        {"name": "withdraw", "sig": "withdraw()", "vis": "external", "modifiers": [],
         "reads": ["balances"], "writes": ["balances"], "calls": ["_pay"], "external_calls": [],
         "payable": False, "low_level": True},
        {"name": "_pay", "sig": "_pay()", "vis": "internal", "modifiers": [],
         "reads": [], "writes": [], "calls": [], "external_calls": [], "payable": False, "low_level": True},
        {"name": "pause", "sig": "pause()", "vis": "external", "modifiers": ["onlyOwner"],
         "reads": [], "writes": ["paused"], "calls": [], "external_calls": [], "payable": False, "low_level": False},
    ]}]}


def test_kg_build_and_queries():
    g = KnowledgeGraph.from_model(MODEL)
    assert "func:Vault.withdraw" in g.nodes and "state:Vault.balances" in g.nodes
    assert ("contract:Vault", "inherits", "contract:Ownable") in g.edges
    assert "func:Vault.pause" in g.privileged_functions()
    assert "func:Vault.withdraw" in g.functions_touching("balances")
    # withdraw is external, writes balances, NOT guarded -> flagged; pause is guarded -> not
    uw = g.unguarded_state_writers()
    assert "func:Vault.withdraw" in uw and "func:Vault.pause" not in uw


def test_kg_save(tmp_path):
    g = KnowledgeGraph.from_model(MODEL)
    g.save(str(tmp_path / "kg.db"))
    assert g.stats()["nodes"]["Function"] == 3
