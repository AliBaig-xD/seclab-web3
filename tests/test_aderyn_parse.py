from orchestrator.tools.aderyn import parse_aderyn_json

SAMPLE = {
    "high_issues": {"issues": [{
        "title": "ETH transferred without address checks",
        "description": "Consider introducing checks for msg.sender.",
        "detector_name": "eth-send-unchecked-address",
        "instances": [{"contract_path": "src/EtherStore.sol", "line_no": 8}],
    }]},
    "low_issues": {"issues": []},
}


def test_parse_aderyn():
    res = parse_aderyn_json(SAMPLE)
    assert len(res) == 1
    h, ev = res[0]
    assert h.vuln_type == "eth-send-unchecked-address"
    assert h.location == "src/EtherStore.sol:8"
    assert ev.kind == "aderyn" and ev.severity_hint == "HIGH"


def test_parse_aderyn_empty():
    assert parse_aderyn_json({}) == []
