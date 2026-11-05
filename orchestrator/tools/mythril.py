"""Mythril adapter (isolated custom image). Symbolic analysis -> SWC issues mapped to
vuln families, so results correlate with static findings (independent corroboration).
Multi-file via forge flatten; single-file direct."""
from __future__ import annotations
import json, os, re, glob, subprocess
from ..schema import Hypothesis, Evidence
from .base import SCRATCH, IMAGE, DOCKER_SAFE, run_tool

MYTH_IMAGE = os.environ.get("SECLAB_MYTHRIL_IMAGE", "seclab-web3/mythril:latest")
SWC_FAMILY = {
    "107": "reentrancy", "101": "arithmetic", "104": "unchecked-return",
    "112": "delegatecall", "115": "tx-origin-auth", "114": "front-running",
    "116": "block-timestamp-randomness", "120": "weak-randomness",
    "105": "unprotected-ether-withdrawal", "106": "unprotected-selfdestruct",
    "100": "function-default-visibility", "108": "state-default-visibility",
}
SEV_MAP = {"High": "HIGH", "Medium": "MEDIUM", "Low": "LOW"}


def parse_mythril_json(data: dict, relpath: str):
    out = []
    if not isinstance(data, dict):
        return out
    for i in data.get("issues", []):
        swc = str(i.get("swc-id", ""))
        fam = SWC_FAMILY.get(swc, f"swc-{swc}")
        line = i.get("lineno", "?")
        title = i.get("title", "")
        sev = i.get("severity", "Low")
        h = Hypothesis(vuln_type=fam, location=f"{relpath}:{line}",
                       precondition="(symbolic reachability proven by mythril)",
                       claimed_impact=f"SWC-{swc}: {title}"[:200],
                       source="symbolic", rationale=f"mythril SWC-{swc}")
        ev = Evidence(kind="mythril", tool="mythril",
                      summary=f"SWC-{swc} [{sev}] {title}"[:140],
                      severity_hint=SEV_MAP.get(sev, "LOW"))
        out.append((h, ev))
    return out


def _solv(src: str) -> str:
    m = re.search(r"pragma solidity[^0-9]*([0-9]+\.[0-9]+\.[0-9]+)", src)
    return m.group(1) if m else "0.8.20"


class MythrilScanner:
    kind = "mythril"
    def __init__(self, exec_timeout: int = 90):
        self.exec_timeout = exec_timeout

    def _analyze_source(self, src_text: str, solv: str, rel: str):
        import hashlib
        work = f"{SCRATCH}/myth-{os.getpid()}-{hashlib.md5(rel.encode()).hexdigest()[:8]}"
        subprocess.run(["sudo", "rm", "-rf", work])
        os.makedirs(work, exist_ok=True)
        with open(os.path.join(work, "flat.sol"), "w") as fh:
            fh.write(src_text)
        cmd = ["docker", "run", "--rm", *DOCKER_SAFE, "-v", f"{work}:/work", "-w", "/work", MYTH_IMAGE,
               "analyze", "flat.sol", "--solv", solv, "-o", "json",
               "--execution-timeout", str(self.exec_timeout)]
        out = []
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=self.exec_timeout + 180)
            data = json.loads(p.stdout)
            if data.get("success"):
                out = parse_mythril_json(data, rel)
        except Exception:
            pass
        subprocess.run(["sudo", "rm", "-rf", work])
        return out

    def scan(self, target_dir: str):
        files = []
        for base in ("src", "contracts"):
            files += glob.glob(os.path.join(target_dir, base, "**", "*.sol"), recursive=True)
        out = []
        for f in sorted(set(files)):
            try:
                src = open(f).read()
            except Exception:
                continue
            rel = os.path.relpath(f, target_dir)
            if "import " in src:
                # flatten (analysis image) so mythril sees a single self-contained file
                rc, flat, _ = run_tool(target_dir, f"forge flatten {rel} 2>/dev/null")
                if flat and ("pragma solidity" in flat and "contract " in flat):
                    src = flat
                else:
                    continue
            if len(src) > 60000:
                continue
            out += self._analyze_source(src, _solv(src), rel)
        return out
