"""Medusa adapter: coverage-guided fuzzing (Go). A FAILED property/assertion test with
a shrunk call sequence is dynamic evidence. Runs in a scratch copy to avoid litter."""
from __future__ import annotations
import os, re, subprocess
from ..schema import Hypothesis, Evidence
from .base import IMAGE, SCRATCH, DOCKER_SAFE

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def parse_medusa_text(text: str):
    text = ANSI.sub("", text)
    res = {}
    for m in re.finditer(r"\[(PASSED|FAILED)\]\s+(Property Test|Assertion Test):\s+(\S+)", text):
        status, ttype, target = m.group(1), m.group(2), m.group(3)
        failed = status == "FAILED"
        prev = res.get(target)
        if prev is None or (failed and not prev["failed"]):
            res[target] = {"failed": failed, "type": ttype}
    return res


class MedusaScanner:
    kind = "medusa"
    def __init__(self, test_limit: int = 20000, timeout: int = 600):
        self.test_limit = test_limit
        self.timeout = timeout

    def scan(self, target_dir: str):
        work = f"{SCRATCH}/medusa-run-{os.getpid()}"
        subprocess.run(["sudo", "rm", "-rf", work])
        subprocess.run(["cp", "-r", target_dir, work])
        script = (
            'medusa init >/dev/null 2>&1 || true; '
            '[ -f medusa.json ] || exit 0; '
            'jq ".fuzzing.testLimit=%d | '
            '.fuzzing.testing.propertyTesting.testPrefixes=[\\"echidna_\\",\\"property_\\",\\"invariant_\\"] | '
            '.fuzzing.testing.assertionTesting.enabled=true" medusa.json > m2 && mv m2 medusa.json; '
            'medusa fuzz 2>&1' % self.test_limit
        )
        cmd = ["docker", "run", "--rm", *DOCKER_SAFE, "-e", "HOME=/cache", "-v", f"{SCRATCH}/toolcache:/cache",
               "-v", f"{work}:/work", "-w", "/work", IMAGE, "bash", "-c", script]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout).stdout
        except Exception:
            out = ""
        subprocess.run(["sudo", "rm", "-rf", work])
        findings = []
        for tgt, r in parse_medusa_text(out).items():
            if r["failed"]:
                loc = tgt.replace("()", "")  # normalize to merge with echidna
                h = Hypothesis(vuln_type="invariant-violation", location=loc,
                               precondition="(medusa fuzzing found a breaking sequence)",
                               claimed_impact=f"{r['type']} {tgt} failed under medusa fuzzing"[:200],
                               source="fuzz", rationale="medusa")
                ev = Evidence(kind="medusa", tool="medusa",
                              summary=f"medusa: {r['type']} {tgt} FAILED"[:140],
                              severity_hint="HIGH", repro=f"medusa fuzz  # {tgt}")
                findings.append((h, ev))
        return findings
