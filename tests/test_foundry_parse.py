from orchestrator.tools.foundry import parse_forge_json

SAMPLE = {
    "test/Exploit.t.sol:ExploitTest": {
        "test_results": {
            "test_exploit_drains_store()": {"status": "Success"},
            "test_other()": {"status": "Failure"},
        }
    }
}


def test_parse_forge_json():
    r = parse_forge_json(SAMPLE)
    assert r["test_exploit_drains_store()"] is True
    assert r["test_other()"] is False


def test_parse_empty():
    assert parse_forge_json({}) == {}
