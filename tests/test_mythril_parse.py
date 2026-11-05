from orchestrator.tools.mythril import parse_mythril_json

SAMPLE = {"success": True, "issues": [
    {"swc-id": "107", "title": "State access after external call",
     "severity": "Medium", "lineno": 13, "function": "withdraw()"},
    {"swc-id": "114", "title": "Transaction Order Dependence",
     "severity": "Medium", "lineno": 11},
]}


def test_parse_mythril_maps_swc_to_family():
    res = parse_mythril_json(SAMPLE, "src/EtherStore.sol")
    assert len(res) == 2
    fams = {h.vuln_type for h, _ in res}
    assert "reentrancy" in fams and "front-running" in fams
    h, ev = res[0]
    assert ev.kind == "mythril" and h.location.startswith("src/EtherStore.sol")


def test_parse_mythril_empty():
    assert parse_mythril_json({}, "x.sol") == []
