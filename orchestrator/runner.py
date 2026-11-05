"""Verification runner: the harness core. The model's hypotheses are routed to
verifiers; the finding tier is derived from collected evidence; an adversarial
reviewer may falsify before anything becomes reportable (docs/WORKFLOW.md L2)."""
from __future__ import annotations
from typing import Iterable
from .schema import Hypothesis, Finding, Evidence
from .evidence import EvidenceStore


class Runner:
    def __init__(self, store: EvidenceStore, verifiers: list, reviewer=None):
        self.store = store
        self.verifiers = verifiers
        self.reviewer = reviewer

    def run(self, run_id: str, target: str, hypotheses: Iterable[Hypothesis]) -> list[Finding]:
        self.store.start_run(run_id, target)
        findings: list[Finding] = []
        for h in hypotheses:
            f = Finding(hypothesis=h)
            if h.source == "llm":
                f.evidence.append(Evidence(kind="llm", tool="model",
                                           summary=h.rationale or h.claimed_impact,
                                           deterministic=False))
            for v in self.verifiers:
                try:
                    ev = v.verify(h, target)
                except Exception as exc:  # a tool failure never fabricates evidence
                    ev = None
                    f.notes += f"[verifier {getattr(v,'kind','?')} error: {exc}] "
                if ev:
                    f.evidence.append(ev)
            f.recompute_tier()
            if self.reviewer is not None and f.reportable:
                if self.reviewer.falsify(f, target):
                    f.falsified = True
                    f.recompute_tier()
            self.store.save_finding(run_id, f)
            findings.append(f)
        return findings
