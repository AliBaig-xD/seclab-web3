import json
from orchestrator.schema import Hypothesis, Finding, Evidence, Severity
from orchestrator.flywheel import emit_training_examples


def test_emit_detection_and_poc(tmp_path):
    poc = tmp_path / "poc.sol"
    poc.write_text(
        "// SPDX-License-Identifier: MIT\npragma solidity ^0.8.20;\n"
        "import \"../src/Vault.sol\";\ncontract PoC is Test {\n"
        "    Vault v;\n    function setUp() public { v = new Vault(); }\n"
        "    function test_exploit() public { require(address(v).balance == 0, \"drained\"); }\n}\n")
    f = Finding(hypothesis=Hypothesis("reentrancy", "src/Vault.sol:8", "p", "drains funds"),
                evidence=[Evidence(kind="foundry_poc", tool="forge", summary="x", repro="r",
                                   artifact_path=str(poc))], repro_cmd="r")
    f.severity = Severity.HIGH
    f.recompute_tier()
    out = tmp_path / "verified.jsonl"
    n = emit_training_examples([f], {"vault": "contract Vault { }"}, out_path=str(out))
    rows = [json.loads(l) for l in open(out)]
    caps = {r["capability"] for r in rows}
    assert "A" in caps and "C" in caps and n >= 2
    assert any("test_exploit" in r["output"] for r in rows if r["capability"] == "C")


def test_skip_unreportable(tmp_path):
    f = Finding(hypothesis=Hypothesis("x", "a:1", "p", "i"))
    f.recompute_tier()
    out = tmp_path / "v.jsonl"
    assert emit_training_examples([f], {"x": "c"}, out_path=str(out)) == 0


def test_load_verified(tmp_path):
    from training.data_pipeline import load_verified
    p = tmp_path / "verified.jsonl"
    p.write_text(json.dumps({"capability": "A", "vuln_class": "reentrancy",
                             "instruction": "analyze", "input": "contract C {}",
                             "output": "reentrancy"}) + "\n")
    ex = load_verified(str(p))
    assert len(ex) == 1 and ex[0].capability == "A" and ex[0].source == "verified-flywheel"
