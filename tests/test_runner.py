from orchestrator.schema import Hypothesis, Evidence, Tier
from orchestrator.evidence import EvidenceStore
from orchestrator.runner import Runner


class FakeVer:
    def __init__(self, kind, tool, hit=True):
        self.kind, self.tool, self.hit = kind, tool, hit

    def verify(self, h, target):
        return Evidence(kind=self.kind, tool=self.tool, summary="hit") if self.hit else None


class FakeReviewer:
    def __init__(self, falsify_ids=()):
        self.ids = set(falsify_ids)

    def falsify(self, finding, target):
        return finding.hypothesis.id in self.ids


def H(t="reentrancy"):
    return Hypothesis(vuln_type=t, location="V.sol:1", precondition="p",
                      claimed_impact="i", source="llm")


def test_two_verifiers_corroborate_and_persist(tmp_path):
    s = EvidenceStore(str(tmp_path / "e.db"))
    r = Runner(s, [FakeVer("slither", "slither"), FakeVer("mythril", "mythril")])
    fs = r.run("r1", "repoA", [H()])
    assert fs[0].tier == Tier.CORROBORATED and fs[0].reportable
    assert len(s.reportable_findings("r1")) == 1


def test_single_verifier_stays_candidate(tmp_path):
    s = EvidenceStore(str(tmp_path / "e.db"))
    r = Runner(s, [FakeVer("slither", "slither")])
    fs = r.run("r1", "repoA", [H()])
    assert fs[0].tier == Tier.CANDIDATE and not fs[0].reportable
    assert s.reportable_findings("r1") == []


def test_reviewer_falsifies_demotes(tmp_path):
    s = EvidenceStore(str(tmp_path / "e.db"))
    h = H()
    r = Runner(s, [FakeVer("slither", "slither"), FakeVer("mythril", "mythril")],
               reviewer=FakeReviewer([h.id]))
    fs = r.run("r1", "repoA", [h])
    assert fs[0].falsified and fs[0].tier == Tier.CANDIDATE and not fs[0].reportable


def test_verifier_exception_is_not_evidence(tmp_path):
    class Boom:
        kind = "boom"
        def verify(self, h, target):
            raise RuntimeError("tool crashed")
    s = EvidenceStore(str(tmp_path / "e.db"))
    r = Runner(s, [Boom(), FakeVer("slither", "slither")])
    fs = r.run("r1", "repoA", [H()])
    # one real tool + crash -> still candidate, crash recorded in notes
    assert fs[0].tier == Tier.CANDIDATE
    assert "error" in fs[0].notes
