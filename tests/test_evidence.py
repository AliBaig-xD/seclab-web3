from orchestrator.schema import Hypothesis, Finding, Evidence
from orchestrator.evidence import EvidenceStore


def test_roundtrip_and_reportable(tmp_path):
    s = EvidenceStore(str(tmp_path / "e.db"))
    s.start_run("r1", "repoA")
    f = Finding(
        hypothesis=Hypothesis(vuln_type="reentrancy", location="V.sol:1",
                              precondition="p", claimed_impact="i"),
        evidence=[Evidence(kind="slither", tool="slither", summary="x"),
                  Evidence(kind="mythril", tool="mythril", summary="y")],
    )
    f.recompute_tier()
    s.save_finding("r1", f)
    rep = s.reportable_findings("r1")
    assert len(rep) == 1
    assert rep[0]["tier"] == "CORROBORATED"
    assert rep[0]["vuln_type"] == "reentrancy"


def test_candidate_not_reportable(tmp_path):
    s = EvidenceStore(str(tmp_path / "e.db"))
    s.start_run("r1", "repoA")
    f = Finding(hypothesis=Hypothesis(vuln_type="x", location="a:1",
                                      precondition="p", claimed_impact="i"))
    f.recompute_tier()
    s.save_finding("r1", f)
    assert s.reportable_findings("r1") == []
