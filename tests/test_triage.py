from orchestrator.schema import Hypothesis, Finding, Evidence, Tier, Severity
from orchestrator import triage


def mkf(vt, sev, tier, reportable=True):
    f = Finding(hypothesis=Hypothesis(vuln_type=vt, location="a:1", precondition="p", claimed_impact="i"))
    f.severity = sev
    if reportable:
        f.evidence = [Evidence(kind="slither", tool="slither", summary="x"),
                      Evidence(kind="mythril", tool="mythril", summary="y")]
    f.recompute_tier()
    return f


def test_value_orders_by_severity_and_tier():
    hi = mkf("a", Severity.CRITICAL, Tier.CORROBORATED)
    lo = mkf("b", Severity.LOW, Tier.CORROBORATED)
    ranked, _ = triage.rank([lo, hi])
    assert [f.hypothesis.vuln_type for f in ranked] == ["a", "b"]


def test_candidates_go_to_not_recommending():
    rep = mkf("a", Severity.HIGH, Tier.CORROBORATED)
    cand = mkf("b", Severity.HIGH, Tier.CANDIDATE, reportable=False)
    ranked, not_rec = triage.rank([rep, cand])
    assert len(ranked) == 1 and len(not_rec) == 1
    assert not_rec[0].hypothesis.vuln_type == "b"


def test_top_n_overflow_demoted():
    fs = [mkf(c, Severity.HIGH, Tier.CORROBORATED) for c in "abc"]
    ranked, not_rec = triage.rank(fs, top_n=2)
    assert len(ranked) == 2 and len(not_rec) == 1
