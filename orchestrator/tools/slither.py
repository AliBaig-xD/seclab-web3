"""Slither adapter: parse `slither --json` into hypotheses + evidence."""
from __future__ import annotations
from ..schema import Hypothesis, Evidence

DETECTOR_MAP = {
    "reentrancy-eth": "reentrancy",
    "reentrancy-no-eth": "reentrancy",
    "reentrancy-benign": "reentrancy",
    "arbitrary-send-eth": "unprotected-ether-withdrawal",
    "suicidal": "unprotected-selfdestruct",
    "unprotected-upgrade": "unprotected-upgrade",
    "tx-origin": "tx-origin-auth",
    "unchecked-transfer": "unchecked-return",
    "weak-prng": "weak-randomness",
}


def _first_loc(elements: list[dict]) -> str:
    for e in elements:
        sm = e.get("source_mapping") or {}
        fn = sm.get("filename_relative") or sm.get("filename_short") or sm.get("filename_absolute") or "?"
        lines = sm.get("lines") or []
        return f"{fn}:{lines[0]}" if lines else fn
    return "?"


def parse_slither_json(data: dict):
    """Return list of (Hypothesis, Evidence) from a slither JSON result object."""
    out = []
    for d in (data.get("results") or {}).get("detectors", []):
        check = d.get("check", "unknown")
        impact = d.get("impact", "?")
        desc = (d.get("description") or "").strip()
        loc = _first_loc(d.get("elements", []))
        h = Hypothesis(
            vuln_type=DETECTOR_MAP.get(check, check),
            location=loc,
            precondition="(surfaced by slither detector)",
            claimed_impact=desc[:200],
            source="static",
            rationale=check,
        )
        ev = Evidence(kind="slither", tool="slither",
                      summary=f"{check} [{impact}] {desc[:120]}")
        out.append((h, ev))
    return out
