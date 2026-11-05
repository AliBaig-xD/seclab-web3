"""Deterministic triage: rank proof-gated findings by value, cap to top-N, and keep
an explicit not-recommending list (never a raw finding dump)."""
from __future__ import annotations
from .schema import Finding, Tier, Severity

SEV_W = {Severity.CRITICAL: 5, Severity.HIGH: 4, Severity.MEDIUM: 3,
         Severity.LOW: 2, Severity.INFO: 1, Severity.UNKNOWN: 1}
TIER_W = {Tier.PROVEN: 3, Tier.CORROBORATED: 2, Tier.CANDIDATE: 1}


def value(f: Finding) -> int:
    return SEV_W[f.severity] * TIER_W[f.tier]


def rank(findings: list[Finding], top_n: int | None = None):
    reportable = sorted((f for f in findings if f.reportable),
                        key=lambda f: (-value(f), f.hypothesis.vuln_type))
    not_rec = [f for f in findings if not f.reportable]
    if top_n is not None:
        return reportable[:top_n], reportable[top_n:] + not_rec
    return reportable, not_rec
