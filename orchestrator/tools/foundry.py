"""Foundry adapter: run `forge test --json`, and a PoC verifier that confirms a
hypothesis when its exploit test passes (PROVEN-tier evidence)."""
from __future__ import annotations
import json
from .base import run_tool
from ..schema import Evidence


def parse_forge_json(data: dict) -> dict:
    r = {}
    for _suite, sd in (data or {}).items():
        for t, td in (sd.get("test_results") or {}).items():
            r[t] = (td.get("status") == "Success")
    return r


def run_forge_tests(target_dir: str, timeout: int = 900) -> dict:
    rc, out, err = run_tool(target_dir, "forge test --json 2>/dev/null", timeout)
    try:
        return parse_forge_json(json.loads(out))
    except Exception:
        return {}


def _fam(vt: str) -> str:
    return "reentrancy" if "reentran" in (vt or "").lower() else (vt or "").lower()


class FoundryPoCVerifier:
    kind = "foundry_poc"
    def __init__(self, poc_test: str, vuln_family: str):
        self.poc_test = poc_test
        self.vuln_family = vuln_family
        self._cache = None

    def verify(self, hyp, target_dir):
        if _fam(hyp.vuln_type) != self.vuln_family:
            return None
        if self._cache is None:
            self._cache = run_forge_tests(target_dir)
        passed = any(k.split("(")[0] == self.poc_test and v for k, v in self._cache.items())
        if passed:
            return Evidence(kind="foundry_poc", tool="forge",
                            summary=f"PoC '{self.poc_test}' passed; impact demonstrated on fork",
                            repro=f"forge test --match-test {self.poc_test}",
                            severity_hint="HIGH")
        return None
