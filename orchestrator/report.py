"""Report generator. Body = PROVEN/CORROBORATED only. Candidates/falsified go to a
transparency appendix so nothing unproven is presented as a finding."""
from __future__ import annotations
from .schema import Finding
from . import triage


def render_markdown(meta: dict, findings: list[Finding]) -> str:
    ranked, not_rec = triage.rank(findings, top_n=meta.get("top_n"))
    L = [f"# Security Report — {meta.get('target', '?')}", ""]
    L.append(f"- Run: `{meta.get('run_id', '?')}`")
    L.append(f"- Reportable findings: {len(ranked)} (PROVEN/CORROBORATED only)")
    L.append("")
    if not ranked:
        L.append("_No proof-gated findings._")
    for i, f in enumerate(ranked, 1):
        h = f.hypothesis
        L += [f"## {i}. {h.vuln_type} — {f.tier.value} [{f.severity.value}]",
              f"- Location: `{h.location}`",
              f"- Impact: {h.claimed_impact}",
              f"- Precondition: {h.precondition}"]
        if f.repro_cmd:
            L.append(f"- Repro: `{f.repro_cmd}`")
        L.append("- Evidence:")
        for e in f.evidence:
            L.append(f"  - [{e.kind}/{e.tool}] {e.summary}")
        L.append("")
    proto = meta.get("protocol")
    if proto and any(proto.get(k) for k in ("invariants", "roles", "assumptions", "questions")):
        L += ["---", "## Protocol intelligence"]
        for key, label in [("invariants", "Invariants"), ("roles", "Roles / trust boundaries"),
                           ("assumptions", "Economic assumptions"), ("questions", "Adversarial questions")]:
            vals = proto.get(key) or []
            if vals:
                L.append(f"**{label}:**")
                L += [f"- {v}" for v in vals[:15]]
    if not_rec:
        L += ["---", "## Not reported (unproven candidates / falsified)",
              "_Listed for transparency; not shipped as findings._"]
        for f in not_rec:
            tag = "falsified" if f.falsified else f.tier.value
            L.append(f"- {f.hypothesis.vuln_type} @ `{f.hypothesis.location}` ({tag})")
    return "\n".join(L)
