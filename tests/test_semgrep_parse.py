from orchestrator.tools.semgrep import parse_semgrep_json

SAMPLE = {"results": [{
    "check_id": "seclab-solidity.low-level-call-with-value",
    "path": "src/EtherStore.sol",
    "start": {"line": 11},
    "extra": {"message": "Low-level call forwarding value", "severity": "WARNING"},
}]}


def test_parse_semgrep():
    res = parse_semgrep_json(SAMPLE)
    assert len(res) == 1
    h, ev = res[0]
    assert h.vuln_type == "low-level-call-with-value"
    assert h.location == "src/EtherStore.sol:11"
    assert ev.kind == "semgrep" and ev.severity_hint == "LOW"


def test_parse_semgrep_empty():
    assert parse_semgrep_json({}) == []
