from orchestrator.tools.slither import parse_slither_json

SAMPLE = {
    "success": True,
    "results": {
        "detectors": [
            {
                "check": "reentrancy-eth",
                "impact": "High",
                "confidence": "Medium",
                "description": "Reentrancy in Vault.withdraw()",
                "elements": [
                    {"type": "function", "name": "withdraw",
                     "source_mapping": {"filename_relative": "src/Vault.sol", "lines": [10, 11, 12]}}
                ],
            }
        ]
    },
}


def test_parse_maps_detector_and_location():
    res = parse_slither_json(SAMPLE)
    assert len(res) == 1
    h, ev = res[0]
    assert h.vuln_type == "reentrancy"
    assert h.location == "src/Vault.sol:10"
    assert h.source == "static"
    assert ev.kind == "slither" and "reentrancy-eth" in ev.summary


def test_empty_results():
    assert parse_slither_json({"results": {"detectors": []}}) == []
    assert parse_slither_json({}) == []
