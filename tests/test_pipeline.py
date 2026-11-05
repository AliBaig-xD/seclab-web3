from orchestrator.schema import Hypothesis, Evidence, Tier
from orchestrator.evidence import EvidenceStore
from orchestrator.pipeline import Pipeline


class FakeScanner:
    kind = "slither"
    def scan(self, target):
        h = Hypothesis(vuln_type="reentrancy", location="src/V.sol:8",
                       precondition="ext call", claimed_impact="drain", source="static")
        return [(h, Evidence(kind="slither", tool="slither",
                             summary="reentrancy-eth", severity_hint="HIGH"))]


class FakePoC:
    kind = "foundry_poc"
    def verify(self, h, t):
        if "reentran" in h.vuln_type:
            return Evidence(kind="foundry_poc", tool="forge", summary="poc passed",
                            repro="forge test --match-test x", severity_hint="HIGH")
        return None


def test_pipeline_static_plus_poc_is_proven(tmp_path):
    s = EvidenceStore(str(tmp_path / "e.db"))
    fs = Pipeline(s, [FakeScanner()], [FakePoC()]).run("r1", str(tmp_path), "tgt")
    assert len(fs) == 1
    f = fs[0]
    assert f.tier == Tier.PROVEN and f.reportable
    assert f.repro_cmd and f.severity.value == "HIGH"
    assert len(s.reportable_findings("r1")) == 1


def test_pipeline_static_only_is_candidate(tmp_path):
    s = EvidenceStore(str(tmp_path / "e.db"))
    fs = Pipeline(s, [FakeScanner()], []).run("r1", str(tmp_path), "tgt")
    assert fs[0].tier == Tier.CANDIDATE and not fs[0].reportable


class TwoSourceScanner:
    kind = "slither"
    def scan(self, target):
        from orchestrator.schema import Hypothesis, Evidence
        a = Hypothesis(vuln_type="reentrancy", location="src/V.sol:8",
                       precondition="p", claimed_impact="drain", source="static")
        b = Hypothesis(vuln_type="Reentrancy", location="V.sol:withdraw",
                       precondition="p", claimed_impact="drain", source="llm")
        return [(a, Evidence(kind="slither", tool="slither", summary="s", severity_hint="HIGH")),
                (b, Evidence(kind="llm", tool="model", summary="l"))]


def test_pipeline_dedups_static_and_llm_by_basename(tmp_path):
    from orchestrator.evidence import EvidenceStore
    from orchestrator.pipeline import Pipeline
    s = EvidenceStore(str(tmp_path / "e.db"))
    fs = Pipeline(s, [TwoSourceScanner()], []).run("r1", str(tmp_path), "tgt")
    assert len(fs) == 1  # src/V.sol and V.sol merge
