"""Responsible-disclosure workflow (completes Phase 6). Turns PROVEN/CORROBORATED findings
into a private disclosure package with severity, repro, remediation, and an ISO/IEC-29147-
style timeline. Only confirmed findings are disclosed; candidates never are."""
from __future__ import annotations
import time
from dataclasses import dataclass

REMEDIATION = {
    "reentrancy": "Apply checks-effects-interactions; update state before external calls; add a reentrancy guard.",
    "access_control": "Restrict the function with an owner/role modifier; never use tx.origin for authorization.",
    "arithmetic": "Use checked arithmetic; round against the user; order multiply-before-divide.",
    "invariant-violation": "Enforce the broken invariant explicitly and add invariant tests.",
    "assertion-violation": "Add the missing precondition/bounds check proven reachable by the counterexample.",
    "unprotected-ether-withdrawal": "Gate value-transfer paths with access control and amount checks.",
}


@dataclass
class DisclosurePolicy:
    contact: str = "security contact of the maintainer / bug-bounty program"
    window_days: int = 90
    standard: str = "ISO/IEC 29147 coordinated disclosure"


def _sev(f):
    return f.severity.value


def build_disclosure(findings, target: str, policy: DisclosurePolicy | None = None) -> dict:
    policy = policy or DisclosurePolicy()
    confirmed = [f for f in findings if f.reportable]
    confirmed.sort(key=lambda f: (0 if f.tier.value == "PROVEN" else 1, f.hypothesis.vuln_type))
    items = []
    for f in confirmed:
        h = f.hypothesis
        items.append({
            "vuln_type": h.vuln_type, "tier": f.tier.value, "severity": _sev(f),
            "location": h.location, "impact": h.claimed_impact,
            "repro": f.repro_cmd, "remediation": REMEDIATION.get(h.vuln_type,
                "Review the flagged code path and add the missing guard/validation."),
            "evidence": [f"{e.kind}:{e.tool}" for e in f.evidence],
        })
    return {
        "target": target, "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "policy": {"contact": policy.contact, "window_days": policy.window_days,
                   "standard": policy.standard},
        "confidentiality": "PRIVATE — share only via the maintainer's security channel.",
        "confirmed_findings": items,
        "note": "Only tool-verified or PoC-reproduced findings are disclosed. PoCs were executed "
                "on a sandboxed fork; no live transaction was broadcast.",
    }


def render_markdown(pkg: dict) -> str:
    L = [f"# Responsible Disclosure — {pkg['target']}", "",
         f"_{pkg['confidentiality']}_", "",
         f"- Generated: {pkg['generated']}",
         f"- Standard: {pkg['policy']['standard']} ({pkg['policy']['window_days']}-day window)",
         f"- Contact: {pkg['policy']['contact']}", ""]
    if not pkg["confirmed_findings"]:
        L.append("_No confirmed findings to disclose._")
    for i, it in enumerate(pkg["confirmed_findings"], 1):
        L += [f"## {i}. {it['vuln_type']} — {it['tier']} [{it['severity']}]",
              f"- Location: `{it['location']}`", f"- Impact: {it['impact']}"]
        if it["repro"]:
            L.append(f"- Reproduction: `{it['repro']}`")
        L += [f"- Evidence: {', '.join(it['evidence'])}",
              f"- Remediation: {it['remediation']}", ""]
    L.append("\n" + pkg["note"])
    return "\n".join(L)
