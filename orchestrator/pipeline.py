"""Correlation pipeline. Static scanners seed findings (keyed by vuln-family + file);
the LLM researcher may add hypotheses; verifiers attach confirming evidence; the
Finding's tier is derived from the accumulated evidence (docs/WORKFLOW.md L2)."""
from __future__ import annotations
import os
from .schema import Hypothesis, Finding, Evidence, Severity
from .evidence import EvidenceStore
from .triage import SEV_W


def family(vt: str) -> str:
    v = (vt or "").lower()
    return "reentrancy" if "reentran" in v else v


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
                 reviewer=None, researcher=None, llm_code=None):
        self.store = store
        self.scanners = scanners
        self.verifiers = verifiers
        self.reviewer = reviewer
        self.researcher = researcher
        self.llm_code = llm_code

    def run(self, run_id: str, target_dir: str, target_id: str):
        self.store.start_run(run_id, target_id)
        fmap: dict = {}

        def add(h: Hypothesis, ev: Evidence | None = None) -> Finding:
            key = (family(h.vuln_type), os.path.basename(h.location.split(":")[0]))
            f = fmap.get(key)
            if f is None:
                f = Finding(hypothesis=h)
                fmap[key] = f
            if ev:
                f.evidence.append(ev)
            return f

        for sc in self.scanners:
            for h, ev in sc.scan(target_dir):
                add(h, ev)

        if self.researcher is not None and self.llm_code:
            for h in self.researcher.hypothesize(self.llm_code):
                f = add(h)
                f.evidence.append(Evidence(kind="llm", tool="model",
                                           summary=h.rationale or h.claimed_impact,
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
                if e.kind in ("foundry_poc", "echidna", "medusa") and e.repro and not f.repro_cmd:
                    f.repro_cmd = e.repro
            f.severity = _severity(f)
            f.recompute_tier()
            if self.reviewer is not None and f.reportable and self.reviewer.falsify(f, target_dir):
                f.falsified = True
                f.recompute_tier()
            self.store.save_finding(run_id, f)
        return findings
