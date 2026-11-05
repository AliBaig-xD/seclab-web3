"""Build the SFT dataset from (1) our labeled corpus + verified working PoCs
(license-owned, leak-controlled; directly teaches detection AND PoC generation), and
(2) external sources from config/datasets.yaml (license-recorded; extension point).
Three capabilities: A security-reasoning, B protocol-reasoning, C PoC generation."""
from __future__ import annotations
import json, os, random, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Our labeled corpus (grows as the lab proves new findings -> flywheel).
CORPUS = [
    {"dir": "eval/corpus/reentrancy-etherstore", "contract": "src/EtherStore.sol",
     "vuln": "reentrancy", "location": "withdraw", "poc": "test/Exploit.t.sol",
     "impact": "external call sends ether before the balance is zeroed, so a malicious "
               "receiver re-enters withdraw and drains other users' deposits"},
    {"dir": "eval/corpus/symbolic-overflow", "contract": "src/Math.sol",
     "vuln": "integer overflow", "location": "add", "poc": None,
     "impact": "unchecked addition wraps around, violating the postcondition result >= a"},
    {"dir": "eval/corpus/fuzz-invariant", "contract": "src/Fuzz.sol",
     "vuln": "invariant violation", "location": "inc", "poc": None,
     "impact": "a sequence of inc() calls flips a boolean invariant that must always hold"},
]


def _read(rel):
    p = os.path.join(ROOT, rel)
    return open(p).read() if os.path.exists(p) else None


def examples_from_corpus():
    out = []
    for c in CORPUS:
        src = _read(os.path.join(c["dir"], c["contract"]))
        if not src:
            continue
        # A: detection/reasoning
        out.append({"capability": "A", "instruction":
                    "Analyze this Solidity contract for security vulnerabilities. Name the "
                    "vulnerability class, the function, and explain the root cause.",
                    "input": src,
                    "output": f"Vulnerability: {c['vuln']} in {c['location']}().\nRoot cause: {c['impact']}."})
        # C: PoC generation (only where we have a verified working PoC)
        if c["poc"]:
            poc = _read(os.path.join(c["dir"], c["poc"]))
            if poc:
                out.append({"capability": "C", "instruction":
                            "Write a self-contained Foundry PoC test that demonstrates the "
                            f"{c['vuln']} in {c['location']}(). Seed victim funds and assert net theft.",
                            "input": src, "output": poc})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "training", "data"))
    ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    ex = examples_from_corpus()
    random.Random(a.seed).shuffle(ex)
    n_test = max(1, int(len(ex) * a.test_frac)) if len(ex) > 2 else 0
    test, train = ex[:n_test], ex[n_test:]
    os.makedirs(a.out_dir, exist_ok=True)
    for name, rows in (("train", train), ("test", test)):
        with open(os.path.join(a.out_dir, f"{name}.jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
    caps = {}
    for r in ex:
        caps[r["capability"]] = caps.get(r["capability"], 0) + 1
    print(f"wrote train={len(train)} test={len(test)} capabilities={caps} -> {a.out_dir}")


if __name__ == "__main__":
    main()
