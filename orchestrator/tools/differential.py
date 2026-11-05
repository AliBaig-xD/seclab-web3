"""Differential testing: run a target's Foundry tests under multiple solc versions and
flag tests whose pass/fail DIVERGES — a signal of version-dependent behavior or optimizer
miscompilation. Part of the validation lab's 'differential' capability."""
from __future__ import annotations
import json, os, subprocess
from ..schema import Hypothesis, Evidence
from .base import IMAGE, SCRATCH
from .foundry import parse_forge_json


def run_with_solc(target_dir: str, solc_version: str, timeout: int = 400) -> dict:
    cache = f"{SCRATCH}/toolcache"
    os.makedirs(cache, exist_ok=True)
    cmd = ["docker", "run", "--rm", "-e", "HOME=/cache", "-v", f"{cache}:/cache",
           "-v", f"{target_dir}:/work", "-w", "/work", IMAGE, "bash", "-c",
           f"forge test --use {solc_version} --json 2>/dev/null"]
    try:
        return parse_forge_json(json.loads(subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout).stdout))
    except Exception:
        return {}


def diff_results(a: dict, b: dict) -> list[str]:
    """Tests whose pass/fail differs between two runs (present+differing in both)."""
    return sorted(t for t in (set(a) | set(b))
                  if t in a and t in b and a[t] != b[t])


class DifferentialScanner:
    kind = "differential"
    def __init__(self, versions=("0.8.19", "0.8.28"), timeout: int = 400):
        self.versions = list(versions)
        self.timeout = timeout

    def scan(self, target_dir: str):
        if not os.path.isdir(os.path.join(target_dir, "test")):
            return []
        runs = {v: run_with_solc(target_dir, v, self.timeout) for v in self.versions}
        out = []
        base = self.versions[0]
        for v in self.versions[1:]:
            for t in diff_results(runs[base], runs[v]):
                h = Hypothesis(vuln_type="compiler-version-divergence", location=t,
                               precondition=f"behavior differs between solc {base} and {v}",
                               claimed_impact=f"test {t} passes under one solc version and fails under another",
                               source="differential", rationale="differential")
                ev = Evidence(kind="differential", tool="forge",
                              summary=f"{t} diverges: solc {base}={runs[base].get(t)} vs {v}={runs[v].get(t)}",
                              severity_hint="MEDIUM",
                              repro=f"forge test --use {base} --match-test {t.split('(')[0]}")
                out.append((h, ev))
        return out
