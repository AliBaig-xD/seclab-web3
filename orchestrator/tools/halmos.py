"""Halmos adapter: run symbolic `check_*` tests; a failing check with a concrete
counterexample is strong (symbolic) evidence of a property violation."""
from __future__ import annotations
import json, os, subprocess
from ..schema import Hypothesis, Evidence
from .base import IMAGE, SCRATCH


def parse_halmos_json(data: dict) -> dict:
    res = {}
    for _suite, tests in (data.get("test_results") or {}).items():
        for t in tests:
            name = (t.get("name") or "").split("(")[0]
            failed = t.get("exitcode", 0) != 0 and t.get("num_models", 0) > 0
            cex = None
            if failed and t.get("models"):
                m = (t["models"][0] or {}).get("model", {})
                cex = {v.get("variable_name", k): v.get("value") for k, v in m.items()}
            res[name] = {"failed": failed, "counterexample": cex}
    return res


def run_halmos(target_dir: str, timeout: int = 600) -> dict:
    cache = f"{SCRATCH}/toolcache"
    os.makedirs(cache, exist_ok=True)
    cmd = ["docker", "run", "--rm", "-e", "HOME=/cache", "-v", f"{cache}:/cache",
           "-v", f"{target_dir}:/work", "-w", "/work", IMAGE, "bash", "-c",
           "halmos --json-output /tmp/h.json >/dev/null 2>&1; cat /tmp/h.json"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return parse_halmos_json(json.loads(p.stdout))
    except Exception:
        return {}


def _fam(vt: str) -> str:
    return "reentrancy" if "reentran" in (vt or "").lower() else (vt or "").lower()


class HalmosScanner:
    kind = "halmos"
    def __init__(self, timeout: int = 600):
        self.timeout = timeout

    def scan(self, target_dir: str):
        out = []
        for name, r in run_halmos(target_dir, self.timeout).items():
            if r["failed"]:
                cex = r.get("counterexample") or {}
                h = Hypothesis(vuln_type="assertion-violation", location=name,
                               precondition="(symbolic counterexample exists)",
                               claimed_impact=f"check {name} violated; counterexample {cex}"[:200],
                               source="symbolic", rationale="halmos")
                ev = Evidence(kind="halmos", tool="halmos",
                              summary=f"halmos counterexample: {name} {cex}"[:140],
                              severity_hint="HIGH", repro=f"halmos --function {name}")
                out.append((h, ev))
        return out


class HalmosVerifier:
    kind = "halmos"
    def __init__(self, check_name: str, vuln_family: str):
        self.check = check_name
        self.vuln_family = vuln_family
        self._cache = None

    def verify(self, hyp, target_dir):
        if _fam(hyp.vuln_type) != self.vuln_family:
            return None
        if self._cache is None:
            self._cache = run_halmos(target_dir)
        r = self._cache.get(self.check)
        if r and r["failed"]:
            return Evidence(kind="halmos", tool="halmos",
                            summary=f"symbolic counterexample for {self.check}: {r.get('counterexample')}"[:140],
                            repro=f"halmos --function {self.check}", severity_hint="HIGH")
        return None
