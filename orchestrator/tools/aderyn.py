"""Aderyn adapter: parse Aderyn JSON report into (Hypothesis, Evidence)."""
from __future__ import annotations
import json
from ..schema import Hypothesis, Evidence
from .base import run_tool

SEV_GROUPS = {"critical_issues": "CRITICAL", "high_issues": "HIGH",
              "medium_issues": "MEDIUM", "low_issues": "LOW"}


def parse_aderyn_json(data: dict):
    out = []
    for group, sev in SEV_GROUPS.items():
        g = data.get(group) or {}
        for issue in g.get("issues", []):
            det = issue.get("detector_name", "unknown")
            title = issue.get("title", "")
            desc = issue.get("description", "")
            inst = (issue.get("instances") or [{}])[0]
            loc = f"{inst.get('contract_path', '?')}:{inst.get('line_no', '?')}"
            h = Hypothesis(vuln_type=det, location=loc,
                           precondition="(surfaced by aderyn detector)",
                           claimed_impact=f"{title}: {desc}"[:200],
                           source="static", rationale=det)
            ev = Evidence(kind="aderyn", tool="aderyn",
                          summary=f"{det} [{sev}] {title}"[:140], severity_hint=sev)
            out.append((h, ev))
    return out


class AderynScanner:
    kind = "aderyn"
    def scan(self, target_dir: str):
        # write report to container-internal /tmp (discarded on --rm; no litter)
        rc, out, err = run_tool(
            target_dir, "aderyn . -o /tmp/ad.json >/dev/null 2>&1; cat /tmp/ad.json")
        try:
            data = json.loads(out)
        except Exception:
            return []
        return parse_aderyn_json(data)
