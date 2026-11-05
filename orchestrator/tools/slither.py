"""Slither adapter: parse JSON into (Hypothesis, Evidence); real scanner runs it."""
from __future__ import annotations
import json
from ..schema import Hypothesis, Evidence
from .base import run_tool

DETECTOR_MAP = {
    "reentrancy-eth": "reentrancy", "reentrancy-no-eth": "reentrancy",
    "reentrancy-benign": "reentrancy", "reentrancy-events": "reentrancy",
    "arbitrary-send-eth": "unprotected-ether-withdrawal",
    "suicidal": "unprotected-selfdestruct", "unprotected-upgrade": "unprotected-upgrade",
    "tx-origin": "tx-origin-auth", "unchecked-transfer": "unchecked-return",
    "weak-prng": "weak-randomness",
}
IMPACT_SEV = {"High": "HIGH", "Medium": "MEDIUM", "Low": "LOW",
              "Informational": "INFO", "Optimization": "INFO"}


def _first_loc(elements):
    for e in elements:
        sm = e.get("source_mapping") or {}
        fn = sm.get("filename_relative") or sm.get("filename_short") or sm.get("filename_absolute") or "?"
        lines = sm.get("lines") or []
        return f"{fn}:{lines[0]}" if lines else fn
    return "?"


def parse_slither_json(data: dict):
    out = []
    for d in (data.get("results") or {}).get("detectors", []):
        check = d.get("check", "unknown")
        impact = d.get("impact", "?")
        desc = (d.get("description") or "").strip()
        loc = _first_loc(d.get("elements", []))
        h = Hypothesis(vuln_type=DETECTOR_MAP.get(check, check), location=loc,
                       precondition="(surfaced by slither detector)",
                       claimed_impact=desc[:200], source="static", rationale=check)
        ev = Evidence(kind="slither", tool="slither",
                      summary=f"{check} [{impact}] {desc[:120]}",
                      severity_hint=IMPACT_SEV.get(impact, "UNKNOWN"))
        out.append((h, ev))
    return out


class SlitherScanner:
    kind = "slither"
    def scan(self, target_dir: str):
        rc, out, err = run_tool(target_dir, "slither . --json - 2>/dev/null")
        try:
            data = json.loads(out)
        except Exception:
            return []
        return parse_slither_json(data)
