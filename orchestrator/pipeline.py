"""Correlation pipeline. Static scanners seed findings (keyed by vuln-family + file);
the LLM researcher may add hypotheses; verifiers attach confirming evidence; the
Finding's tier is derived from the accumulated evidence (docs/WORKFLOW.md L2)."""
from __future__ import annotations
import os
from .schema import Hypothesis, Finding, Evidence, Severity
from .evidence import EvidenceStore
from .triage import SEV_W


def loc_key(location: str) -> str:
    """Normalize a location to its contract/file stem so file-based locators
    (src/Vault.sol:42) and symbol-based ones (Vault.withdraw) correlate."""
    head = (location or "").split(":")[0]
    base = os.path.basename(head)
    return (base.split(".")[0] or base).lower()


def family(vt: str) -> str:
    v = (vt or "").lower()
    return "reentrancy" if "reentran" in v else v


def _resolve_source(location: str, source_files: dict):
    stem = loc_key(location)
    for path, content in source_files.items():
        if os.path.basename(path).split(".")[0].lower() == stem:
            return "../" + path, content
    return None, None


def _severity(f: Finding) -> Severity:
    best = Severity.UNKNOWN
    for e in f.evidence:
        if e.severity_hint:
            try:
                s = Severity(e.severity_hint)
            except Exception:
                continue
            if SEV_W[s] > SEV_W[best]:
                best = s
    return best


class Pipeline:
    def __init__(self, store: EvidenceStore, scanners, verifiers,
                 reviewer=None, researcher=None, llm_code=None, protocol=None,
                 seed_hypotheses=None, exploiter=None, source_files=None, max_exploits=5,
                 scanner_concurrency=1):
        self.store = store
        self.scanners = scanners
        self.verifiers = verifiers
        self.reviewer = reviewer
        self.researcher = researcher
        self.llm_code = llm_code
        self.protocol = protocol
        self.protocol_model = None
        self.seed_hypotheses = seed_hypotheses or []
        self.exploiter = exploiter
        self.source_files = source_files or {}
        self.max_exploits = max_exploits
        self.scanner_concurrency = max(1, scanner_concurrency)

    def run(self, run_id: str, target_dir: str, target_id: str):
        self.store.start_run(run_id, target_id)
        self._exploits_left = self.max_exploits
        hints = ""
        if self.protocol is not None and self.llm_code:
            self.protocol_model = self.protocol.analyze(self.llm_code)
            leads = (self.protocol_model.get("questions", []) +
                     self.protocol_model.get("invariants", []))
            if leads:
                hints = "Protocol-level leads to investigate:\n" + "\n".join(f"- {q}" for q in leads[:20])
        fmap: dict = {}

        def add(h: Hypothesis, ev: Evidence | None = None) -> Finding:
            key = (family(h.vuln_type), loc_key(h.location))
            f = fmap.get(key)
            if f is None:
                f = Finding(hypothesis=h)
                fmap[key] = f
            if ev:
                f.evidence.append(ev)
            return f

        if self.scanner_concurrency > 1 and len(self.scanners) > 1:
            from concurrent.futures import ThreadPoolExecutor
            def _safe(sc):
                try:
                    return sc.scan(target_dir)
                except Exception:
                    return []
            with ThreadPoolExecutor(max_workers=self.scanner_concurrency) as ex:
                batches = list(ex.map(_safe, self.scanners))
            for batch in batches:
                for h, ev in batch:
                    add(h, ev)
        else:
            for sc in self.scanners:
                try:
                    for h, ev in sc.scan(target_dir):
                        add(h, ev)
                except Exception:
                    pass

        if self.researcher is not None and self.llm_code:
            for h in self.researcher.hypothesize(self.llm_code, hints):
                f = add(h)
                f.evidence.append(Evidence(kind="llm", tool="model",
                                           summary=h.rationale or h.claimed_impact,
                                           deterministic=False))

        for h in self.seed_hypotheses:
            f = add(h)
            f.evidence.append(Evidence(kind="llm", tool="swarm",
                                       summary=(h.rationale or h.claimed_impact)[:140],
                                       deterministic=False))

        findings = list(fmap.values())
        for f in findings:
            for v in self.verifiers:
                try:
                    ev = v.verify(f.hypothesis, target_dir)
                except Exception as exc:
                    ev = None
                    f.notes += f"[verifier {getattr(v, 'kind', '?')} err: {exc}] "
                if ev:
                    f.evidence.append(ev)
            for e in f.evidence:
                if (e.kind in ("foundry_poc", "echidna", "medusa")
                        and e.proof_valid and e.repro and not f.repro_cmd):
                    f.repro_cmd = e.repro
            f.severity = _severity(f)
            f.recompute_tier()
            if (self.exploiter is not None and not f.falsified
                    and f.tier != __import__("orchestrator.schema", fromlist=["Tier"]).Tier.PROVEN
                    and self._exploits_left > 0 and (f.evidence)):
                imp, src = _resolve_source(f.hypothesis.location, self.source_files)
                if imp and src:
                    self._exploits_left -= 1
                    ev, _it = self.exploiter.attempt(f.hypothesis, target_dir, imp, src)
                    if ev:
                        f.evidence.append(ev)
                        if ev.kind == "foundry_poc" and not ev.proof_valid:
                            f.notes += "[insufficient-proof: generated PoC passed without validated mechanism/impact] "
                        if ev.proof_valid and ev.repro and not f.repro_cmd:
                            f.repro_cmd = ev.repro
                        f.recompute_tier()
            if self.reviewer is not None and f.reportable and self.reviewer.falsify(f, target_dir):
                f.falsified = True
                f.recompute_tier()
            self.store.save_finding(run_id, f)
        return findings
