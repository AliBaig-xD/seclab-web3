from orchestrator.reviewer import parse_verdict, LLMReviewer
from orchestrator.schema import Hypothesis, Finding, Evidence


def test_parse_verdict():
    assert parse_verdict("VERDICT: FALSE_POSITIVE\nREASON: guarded") == "false_positive"
    assert parse_verdict("VERDICT: REAL") == "real"
    assert parse_verdict("unsure") == "unknown"


class FP:
    def generate(self, p, system=None):
        return "VERDICT: FALSE_POSITIVE\nREASON: unreachable"


def test_reviewer_never_falsifies_dynamic_proof(tmp_path):
    f = Finding(hypothesis=Hypothesis("reentrancy", "V.sol:1", "p", "i"),
                evidence=[Evidence(kind="foundry_poc", tool="forge", summary="drained", repro="r")],
                repro_cmd="r")
    f.recompute_tier()
    assert LLMReviewer(FP()).falsify(f, str(tmp_path)) is False


def test_reviewer_falsifies_static_candidate(tmp_path):
    f = Finding(hypothesis=Hypothesis("x", "V.sol:1", "p", "i"),
                evidence=[Evidence(kind="slither", tool="slither", summary="s"),
                          Evidence(kind="mythril", tool="mythril", summary="m")])
    f.recompute_tier()
    assert LLMReviewer(FP()).falsify(f, str(tmp_path)) is True
