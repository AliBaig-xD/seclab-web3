"""Echidna adapter: property-based fuzzing. A falsified `echidna_*` property with a
reproducing call sequence is dynamic evidence of an invariant violation."""
from __future__ import annotations
import os, re, glob, subprocess
from ..schema import Hypothesis, Evidence
from .base import IMAGE, SCRATCH, DOCKER_SAFE


def parse_echidna_text(text: str):
    """Return {property_name: {"falsified": bool, "sequence": [calls]}}."""
    res = {}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.search(r"Test (\w+) (falsified|passed|passing)", line)
        if not m:
            continue
        name = m.group(1)
        falsified = "fals" in m.group(2)
        seq = []
        if falsified:
            for j in range(i + 1, min(i + 40, len(lines))):
                if re.search(r"Test \w+ (falsified|passed|passing)", lines[j]):
                    break
                cm = re.search(r"(\w+\.\w+\([^)]*\))", lines[j])
                if cm:
                    seq.append(cm.group(1))
        prev = res.get(name)
        if prev is None or (falsified and not prev["falsified"]):
            res[name] = {"falsified": falsified, "sequence": seq}
    return res


def _contracts_with_properties(target_dir: str):
    names = []
    files = []
    for base in ("src", "contracts"):
        files += glob.glob(os.path.join(target_dir, base, "**", "*.sol"), recursive=True)
    for f in files:
        try:
            src = open(f).read()
        except Exception:
            continue
        if "echidna_" in src:
            names += re.findall(r"\bcontract\s+(\w+)", src)
    return list(dict.fromkeys(names))


class EchidnaScanner:
    kind = "echidna"
    def __init__(self, test_limit: int = 50000, timeout: int = 600):
        self.test_limit = test_limit
        self.timeout = timeout

    def _run(self, target_dir: str, contract: str) -> str:
        cache = f"{SCRATCH}/toolcache"
        os.makedirs(cache, exist_ok=True)
        cmd = ["docker", "run", "--rm", *DOCKER_SAFE, "-e", "HOME=/cache", "-v", f"{cache}:/cache",
               "-v", f"{target_dir}:/work", "-w", "/work", IMAGE, "bash", "-c",
               f"echidna . --contract {contract} --test-mode property --test-limit {self.test_limit} 2>&1"]
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout).stdout
        except Exception:
            return ""

    def scan(self, target_dir: str):
        out = []
        for c in _contracts_with_properties(target_dir):
            for name, r in parse_echidna_text(self._run(target_dir, c)).items():
                if r["falsified"]:
                    seq = " -> ".join(r["sequence"][:12]) or "(sequence found)"
                    h = Hypothesis(vuln_type="invariant-violation", location=f"{c}.{name}",
                                   precondition="(fuzzing found a breaking tx sequence)",
                                   claimed_impact=f"property {name} falsified; seq: {seq}"[:200],
                                   source="fuzz", rationale="echidna")
                    ev = Evidence(kind="echidna", tool="echidna",
                                  summary=f"echidna falsified {name}: {seq}"[:140],
                                  severity_hint="HIGH",
                                  repro=f"echidna . --contract {c} --test-mode property")
                    out.append((h, ev))
        return out
