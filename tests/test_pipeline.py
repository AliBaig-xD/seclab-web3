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


def test_loc_key_normalizes_file_and_symbol_locators():
    from orchestrator.pipeline import loc_key
    assert loc_key("src/EtherStore.sol:8") == "etherstore"
    assert loc_key("EtherStore.withdraw") == "etherstore"
    assert loc_key("EtherStore.sol:withdraw") == "etherstore"


class SymbolScanner:
    kind = "slither"
    def scan(self, target):
        from orchestrator.schema import Hypothesis, Evidence
        a = Hypothesis(vuln_type="reentrancy", location="src/V.sol:8", precondition="p",
                       claimed_impact="drain", source="static")
        b = Hypothesis(vuln_type="Reentrancy", location="V.withdraw", precondition="p",
                       claimed_impact="drain", source="llm")
        return [(a, Evidence(kind="slither", tool="slither", summary="s", severity_hint="HIGH")),
                (b, Evidence(kind="llm", tool="swarm", summary="l"))]


def test_pipeline_merges_file_and_symbol_locations(tmp_path):
    from orchestrator.evidence import EvidenceStore
    from orchestrator.pipeline import Pipeline
    s = EvidenceStore(str(tmp_path / "e.db"))
    fs = Pipeline(s, [SymbolScanner()], []).run("r1", str(tmp_path), "tgt")
    assert len(fs) == 1


class StaticOnly:
    kind = "slither"
    def scan(self, target):
        from orchestrator.schema import Hypothesis, Evidence
        h = Hypothesis("reentrancy", "src/Vault.sol:8", "p", "drain", source="static")
        return [(h, Evidence(kind="slither", tool="slither", summary="s", severity_hint="HIGH"))]


class WinningExploiter:
    def attempt(self, hyp, target_dir, imp, src):
        from orchestrator.schema import Evidence
        return Evidence(kind="foundry_poc", tool="forge", summary="generated PoC passed",
                        repro="forge test --match-contract PoC"), 1


def test_exploiter_upgrades_candidate_to_proven(tmp_path):
    from orchestrator.evidence import EvidenceStore
    from orchestrator.pipeline import Pipeline
    from orchestrator.schema import Tier
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "Vault.sol").write_text("contract Vault {}")
    s = EvidenceStore(str(tmp_path / "e.db"))
    fs = Pipeline(s, [StaticOnly()], [], exploiter=WinningExploiter(),
                  source_files={"src/Vault.sol": "contract Vault {}"}).run("r1", str(tmp_path), "t")
    assert fs[0].tier == Tier.PROVEN and fs[0].repro_cmd
