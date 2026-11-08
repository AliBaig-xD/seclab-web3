from orchestrator.schema import Hypothesis, Finding, Evidence, Severity
from orchestrator.disclosure import build_disclosure, render_markdown, DisclosurePolicy


def _proven():
    f = Finding(hypothesis=Hypothesis("reentrancy", "V.sol:8", "p", "drain funds"),
                evidence=[Evidence(kind="foundry_poc", tool="forge", summary="drained", repro="r",
                                   proof_valid=True, proof={"proof_status": "PROVEN"})],
                repro_cmd="forge test --match-test t")
    f.severity = Severity.HIGH
    f.recompute_tier()
    return f


def _candidate():
    f = Finding(hypothesis=Hypothesis("weak-randomness", "L.sol:9", "p", "predict"))
    f.recompute_tier()
    return f


def test_disclosure_only_confirmed():
    pkg = build_disclosure([_proven(), _candidate()], "repoA", DisclosurePolicy(window_days=30))
    assert len(pkg["confirmed_findings"]) == 1
    it = pkg["confirmed_findings"][0]
    assert it["vuln_type"] == "reentrancy" and it["remediation"]
    assert pkg["policy"]["window_days"] == 30
    md = render_markdown(pkg)
    assert "Responsible Disclosure" in md and "forge test" in md and "weak-randomness" not in md


def test_disclosure_empty():
    md = render_markdown(build_disclosure([_candidate()], "repoA"))
    assert "No confirmed findings" in md
