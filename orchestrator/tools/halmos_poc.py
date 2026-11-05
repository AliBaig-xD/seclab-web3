"""Halmos counterexample -> deterministic Foundry PoC (recall lever #2). A symbolic
counterexample proves an assertion is violable; this plugs the concrete values into a
test that calls the check and asserts it reverts -> if forge confirms, the finding is
PROVEN, with no LLM in the loop."""
from __future__ import annotations
import glob, os, re, subprocess
from .base import IMAGE, SCRATCH, DOCKER_SAFE
from ..schema import Hypothesis, Evidence
from .halmos import run_halmos


def extract_check_params(src: str, check_name: str):
    """Return [(type, name), ...] for a check_ function's parameters, in order."""
    m = re.search(rf"function\s+{re.escape(check_name)}\s*\(([^)]*)\)", src)
    if not m:
        return []
    out = []
    for part in (p.strip() for p in m.group(1).split(",") if p.strip()):
        toks = part.split()
        if len(toks) >= 2:
            out.append((toks[0], toks[-1]))
    return out


def check_contract_of(src: str, check_name: str):
    """Name of the contract that declares check_name (last 'contract X {' before it)."""
    idx = src.find(f"function {check_name}")
    if idx < 0:
        return None
    before = src[:idx]
    ms = list(re.finditer(r"\bcontract\s+(\w+)", before))
    return ms[-1].group(1) if ms else None


def build_halmos_poc(check_contract: str, check_name: str, ordered_values: list, import_path: str) -> str:
    args = ", ".join(str(v) for v in ordered_values)
    return ("// SPDX-License-Identifier: MIT\npragma solidity ^0.8.20;\n"
            f'import "{import_path}";\n'
            f"contract HalmosPoC is {check_contract} {{\n"
            "    function test_counterexample() public {\n"
            f"        try this.{check_name}({args}) {{ revert(\"invariant held\"); }} catch {{ }}\n"
            "    }\n}\n")


def _ordered_values(cex: dict, params):
    vals = []
    for _t, name in params:
        if name in cex:
            vals.append(cex[name])
        else:
            return None
    return vals


class HalmosPoCScanner:
    """Runs Halmos; for each falsified check with a concrete counterexample, synthesizes
    and runs a Foundry PoC that reproduces it -> PROVEN-tier evidence."""
    kind = "foundry_poc"
    def __init__(self, timeout: int = 500):
        self.timeout = timeout

    def _test_sources(self, target_dir):
        src = ""
        for f in glob.glob(os.path.join(target_dir, "test", "**", "*.sol"), recursive=True):
            try:
                src += open(f).read() + "\n"
            except Exception:
                pass
        return src

    def scan(self, target_dir: str):
        results = run_halmos(target_dir, self.timeout)
        tsrc = self._test_sources(target_dir)
        out = []
        for name, r in results.items():
            if not (r["failed"] and r.get("counterexample")):
                continue
            contract = check_contract_of(tsrc, name)
            params = extract_check_params(tsrc, name)
            vals = _ordered_values(r["counterexample"], params)
            if not (contract and params and vals):
                continue
            import_path = None  # test file is at test/; a check inherits locally -> import its own file
            # find the test file declaring the contract, import relative to a new test file
            for f in glob.glob(os.path.join(target_dir, "test", "**", "*.sol"), recursive=True):
                try:
                    if re.search(rf"\bcontract\s+{contract}\b", open(f).read()):
                        import_path = "./" + os.path.basename(f)
                        break
                except Exception:
                    pass
            if not import_path:
                continue
            poc = build_halmos_poc(contract, name, vals, import_path)
            work = f"{SCRATCH}/halmospoc-{os.getpid()}"
            subprocess.run(["sudo", "rm", "-rf", work])
            subprocess.run(["cp", "-r", target_dir, work])
            with open(os.path.join(work, "test", "HalmosPoC.t.sol"), "w") as fh:
                fh.write(poc)
            cmd = ["docker", "run", "--rm", *DOCKER_SAFE, "-e", "HOME=/cache",
                   "-v", f"{SCRATCH}/toolcache:/cache", "-v", f"{work}:/work", "-w", "/work", IMAGE,
                   "bash", "-c", "forge test --match-contract HalmosPoC --json 2>/dev/null"]
            passed = False
            try:
                import json as _json
                from .foundry import parse_forge_json
                res = parse_forge_json(_json.loads(subprocess.run(
                    cmd, capture_output=True, text=True, timeout=self.timeout).stdout))
                passed = any(v for v in res.values())
            except Exception:
                pass
            subprocess.run(["sudo", "rm", "-rf", work])
            if passed:
                h = Hypothesis(vuln_type="assertion-violation", location=name,
                               precondition="(symbolic counterexample reproduced concretely)",
                               claimed_impact=f"check {name} violated by concrete inputs {vals}"[:200],
                               source="symbolic", rationale="halmos->poc")
                ev = Evidence(kind="foundry_poc", tool="forge",
                              summary=f"Halmos counterexample reproduced as a passing PoC for {name}"[:140],
                              repro="forge test --match-contract HalmosPoC", severity_hint="HIGH")
                out.append((h, ev))
        return out
