from orchestrator.schema import Hypothesis, Finding, Evidence, Tier


def mkh():
    return Hypothesis(vuln_type="reentrancy", location="Vault.sol:42",
                      precondition="external call before state update",
                      claimed_impact="drain funds")


def test_candidate_default():
    f = Finding(hypothesis=mkh())
    assert f.recompute_tier() == Tier.CANDIDATE
    assert not f.reportable


def test_corroborated_two_independent_tools():
    f = Finding(hypothesis=mkh(), evidence=[
        Evidence(kind="slither", tool="slither", summary="reentrancy detector"),
        Evidence(kind="mythril", tool="mythril", summary="reachable external call"),
    ])
    assert f.recompute_tier() == Tier.CORROBORATED
    assert f.reportable


def test_proven_needs_poc_and_repro():
    f = Finding(hypothesis=mkh(),
                evidence=[Evidence(kind="foundry_poc", tool="forge", summary="drained 100%",
                                   proof_valid=True, proof={"proof_status": "PROVEN"})],
                repro_cmd="forge test --match-test test_exploit")
    assert f.recompute_tier() == Tier.PROVEN
    assert f.reportable


def test_poc_without_repro_is_not_proven():
    f = Finding(hypothesis=mkh(),
                evidence=[Evidence(kind="foundry_poc", tool="forge", summary="drained")])
    assert f.recompute_tier() == Tier.CANDIDATE
    assert not f.reportable


def test_insufficient_dynamic_proof_does_not_corroborate():
    f = Finding(hypothesis=mkh(), evidence=[
        Evidence(kind="aderyn", tool="aderyn", summary="static detector"),
        Evidence(kind="foundry_poc", tool="forge",
                 summary="passed but insufficient proof"),
    ])
    assert f.recompute_tier() == Tier.CANDIDATE
    assert not f.reportable


def test_single_tool_stays_candidate():
    f = Finding(hypothesis=mkh(),
                evidence=[Evidence(kind="slither", tool="slither", summary="x")])
    assert f.recompute_tier() == Tier.CANDIDATE


def test_falsified_demotes_even_with_poc():
    f = Finding(hypothesis=mkh(),
                evidence=[Evidence(kind="foundry_poc", tool="forge", summary="d")],
                repro_cmd="x", falsified=True)
    assert f.recompute_tier() == Tier.CANDIDATE
    assert not f.reportable


def test_llm_evidence_does_not_count_as_independent():
    f = Finding(hypothesis=mkh(), evidence=[
        Evidence(kind="llm", tool="qwen", summary="looks like reentrancy"),
        Evidence(kind="llm", tool="qwen", summary="again"),
    ])
    assert f.recompute_tier() == Tier.CANDIDATE


def test_hypothesis_id_stable_and_sized():
    assert mkh().id == mkh().id
    assert len(mkh().id) == 12


def test_echidna_falsification_with_repro_is_proven():
    f = Finding(hypothesis=mkh(),
                evidence=[Evidence(kind="echidna", tool="echidna", summary="falsified",
                                   repro="echidna . --contract X", proof_valid=True,
                                   proof={"proof_status": "PROVEN"})],
                repro_cmd="echidna . --contract X")
    assert f.recompute_tier() == Tier.PROVEN and f.reportable
