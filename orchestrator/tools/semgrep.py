"""Semgrep adapter using our own Solidity ruleset (analysis/semgrep-rules)."""
from __future__ import annotations
import json, os, subprocess
from ..schema import Hypothesis, Evidence
from .base import IMAGE, SCRATCH

RULES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "analysis", "semgrep-rules")
SEV = {"ERROR": "MEDIUM", "WARNING": "LOW", "INFO": "INFO"}


def parse_semgrep_json(data: dict):
    out = []
    for r in data.get("results", []):
        cid = (r.get("check_id") or "").split(".")[-1]
        path = r.get("path", "?")
        line = (r.get("start") or {}).get("line", "?")
        extra = r.get("extra") or {}
        msg = extra.get("message", "")
        sev = extra.get("severity", "INFO")
        h = Hypothesis(vuln_type=cid, location=f"{path}:{line}",
                       precondition="(semgrep pattern match)",
                       claimed_impact=msg[:200], source="static", rationale=cid)
        ev = Evidence(kind="semgrep", tool="semgrep",
                      summary=f"{cid} [{sev}] {msg[:100]}", severity_hint=SEV.get(sev, "INFO"))
        out.append((h, ev))
    return out


class SemgrepScanner:
    kind = "semgrep"
    def __init__(self, rules_dir: str = RULES_DIR):
        self.rules = rules_dir

    def scan(self, target_dir: str):
        cache = f"{SCRATCH}/toolcache"
        os.makedirs(cache, exist_ok=True)
        cmd = ["docker", "run", "--rm", "-e", "HOME=/cache",
               "-v", f"{cache}:/cache", "-v", f"{self.rules}:/rules:ro",
               "-v", f"{target_dir}:/work", "-w", "/work", IMAGE,
               "bash", "-c", "semgrep --config /rules --json src 2>/dev/null"]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            return parse_semgrep_json(json.loads(p.stdout))
        except Exception:
            return []
