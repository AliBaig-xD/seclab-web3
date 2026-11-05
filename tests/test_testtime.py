from orchestrator.schema import Hypothesis, Finding, Evidence


def test_multisample_dedups_and_unions():
    from orchestrator.researcher import Researcher
    outs = [
        '[{"vuln_type":"reentrancy","location":"V.sol:8","precondition":"p","claimed_impact":"i"}]',
        '[{"vuln_type":"reentrancy","location":"V.sol:8","precondition":"p","claimed_impact":"i"},'
        ' {"vuln_type":"access-control","location":"A.sol:2","precondition":"p","claimed_impact":"i"}]',
        '[{"vuln_type":"oracle","location":"O.sol:5","precondition":"p","claimed_impact":"i"}]']

    class C:
        def __init__(self): self.i = 0
        def generate(self, prompt, system=None, temperature=None, seed=None):
            o = outs[self.i % len(outs)]; self.i += 1; return o
    hs = Researcher(C(), samples=3).hypothesize("code")
    types = {h.vuln_type for h in hs}
    assert {"reentrancy", "access-control", "oracle"} <= types     # unioned
    assert len([h for h in hs if h.vuln_type == "reentrancy"]) == 1  # deduped


def test_reviewer_majority_vote(tmp_path):
    from orchestrator.reviewer import LLMReviewer
    f = Finding(hypothesis=Hypothesis("x", "V.sol:1", "p", "i"),
                evidence=[Evidence(kind="slither", tool="slither", summary="s"),
                          Evidence(kind="mythril", tool="mythril", summary="m")])
    f.recompute_tier()

    class Vote:
        def __init__(self, seq): self.seq = seq; self.i = 0
        def generate(self, prompt, system=None, temperature=None, seed=None):
            v = self.seq[self.i % len(self.seq)]; self.i += 1
            return "VERDICT: FALSE_POSITIVE" if v else "VERDICT: REAL"
    assert LLMReviewer(Vote([True, True, False]), votes=3).falsify(f, str(tmp_path)) is True   # 2/3
    assert LLMReviewer(Vote([True, False, False]), votes=3).falsify(f, str(tmp_path)) is False  # 1/3
