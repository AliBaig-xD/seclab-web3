"""Self-improvement flywheel: every PROVEN/CORROBORATED finding becomes training data
(detection example + the verified PoC when one exists). The lab learns from what it
proves -- the core way a small model is made to punch above its weight."""
from __future__ import annotations
import json, os
from .pipeline import family, loc_key

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def emit_training_examples(findings, source_by_contract: dict, out_path: str = None) -> int:
    out_path = out_path or os.path.join(ROOT, "training", "data", "verified.jsonl")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    n = 0
    with open(out_path, "a") as f:
        for fd in findings:
            if not fd.reportable:
                continue
            h = fd.hypothesis
            src = source_by_contract.get(loc_key(h.location)) or \
                (next(iter(source_by_contract.values())) if source_by_contract else "")
            if not src or len(src) > 24000:
                continue
            # capability A: detection (verified, so a high-quality label)
            f.write(json.dumps({
                "capability": "A", "vuln_class": family(h.vuln_type),
                "instruction": "Analyze this Solidity contract for security vulnerabilities. Name the "
                               "vulnerability class and the function, and explain the root cause.",
                "input": src,
                "output": f"Vulnerability: {h.vuln_type} at {h.location}.\nRoot cause: {h.claimed_impact}",
                "source": "verified-flywheel", "license": "proprietary-internal"}) + "\n")
            n += 1
            # capability C: the verified PoC (only when one was actually generated + saved)
            for e in fd.evidence:
                if e.kind == "foundry_poc" and e.artifact_path and os.path.exists(e.artifact_path):
                    try:
                        poc = open(e.artifact_path).read()
                    except Exception:
                        continue
                    if 100 < len(poc) < 16000:
                        f.write(json.dumps({
                            "capability": "C", "vuln_class": family(h.vuln_type),
                            "instruction": f"Write a self-contained Foundry PoC that demonstrates the "
                                           f"{h.vuln_type} in this contract. Seed victim funds and assert impact.",
                            "input": src, "output": poc,
                            "source": "verified-flywheel", "license": "proprietary-internal"}) + "\n")
                        n += 1
                    break
    return n
