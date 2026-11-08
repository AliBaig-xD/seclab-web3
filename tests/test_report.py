from orchestrator.schema import Hypothesis, Finding, Evidence, Tier, Severity
from orchestrator.report import render_markdown


def proven():
    f = Finding(hypothesis=Hypothesis(vuln_type="reentrancy", location="V.sol:42",
                                      precondition="ext call", claimed_impact="drain"),
                evidence=[Evidence(kind="foundry_poc", tool="forge", summary="drained 100%",
                                   proof_valid=True, proof={"proof_status": "PROVEN"})],
                repro_cmd="forge test --match-test test_exploit")
    f.severity = Severity.CRITICAL
    f.recompute_tier()
    return f


def candidate():
    f = Finding(hypothesis=Hypothesis(vuln_type="weak-randomness", location="L.sol:9",
                                      precondition="blockhash", claimed_impact="predict"))
    f.recompute_tier()
    return f


def test_body_has_reportable_appendix_has_candidate():
    md = render_markdown({"target": "repoA", "run_id": "r1"}, [proven(), candidate()])
    assert "reentrancy — PROVEN [CRITICAL]" in md
    assert "forge test --match-test test_exploit" in md
    assert "Not reported" in md and "weak-randomness" in md


def test_no_reportable_message():
    md = render_markdown({"target": "repoA", "run_id": "r1"}, [candidate()])
    assert "_No proof-gated findings._" in md
