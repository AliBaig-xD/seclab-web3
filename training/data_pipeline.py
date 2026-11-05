"""Production data curation for seclab-web3 SFT.

Principles (how real teams do it):
- Provenance + license recorded per example.
- Content-hash DEDUP of contracts.
- LEAKAGE-SAFE split BY CONTRACT (all examples of one contract share a split).
- Three capabilities: A security-reasoning, B protocol-reasoning, C PoC generation.
- A data card (sources, licenses, counts, class balance, split sizes, dataset hash).
Add a source by writing a loader that yields Example dicts; the curator does the rest.
"""
from __future__ import annotations
import argparse, glob, hashlib, json, os, re, time
from dataclasses import dataclass, asdict, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.environ.get("SECLAB_SCRATCH", "/opt/dlami/nvme/seclab")

CLASS_EXPLAIN = {
    "reentrancy": "an external call is made before state is updated, letting the callee re-enter and repeat the effect",
    "access_control": "a privileged/state-changing function lacks an owner/role check (or uses tx.origin)",
    "arithmetic": "unchecked over/underflow or unsafe casts corrupt accounting",
    "bad_randomness": "randomness derives from predictable/miner-influenceable chain values",
    "denial_of_service": "an attacker can make a function permanently revert or exhaust gas",
    "front_running": "transaction ordering lets an observer profit by acting first",
    "time_manipulation": "logic depends on miner-influenceable block.timestamp",
    "short_addresses": "insufficient input/length validation of addresses or calldata",
    "unchecked_low_level_calls": "the return value of a low-level call/send is not checked",
    "other": "a security-relevant issue specific to this contract",
}


def _norm(src: str) -> str:
    return re.sub(r"[ \t]+\n", "\n", (src or "").replace("\r\n", "\n")).strip() + "\n"


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "ignore")).hexdigest()


@dataclass
class Example:
    capability: str          # A | B | C
    vuln_class: str
    instruction: str
    input: str
    output: str
    source: str
    license: str
    contract_sha: str
    split: str = ""


# ---------------- loaders ----------------

def load_corpus() -> list[Example]:
    CORPUS = [
        {"dir": "eval/corpus/reentrancy-etherstore", "contract": "src/EtherStore.sol",
         "cls": "reentrancy", "loc": "withdraw", "poc": "test/Exploit.t.sol",
         "impact": CLASS_EXPLAIN["reentrancy"] + "; here withdraw() sends ether before zeroing the balance"},
        {"dir": "eval/corpus/symbolic-overflow", "contract": "src/Math.sol",
         "cls": "arithmetic", "loc": "add", "poc": None,
         "impact": "unchecked addition wraps, violating result >= a"},
        {"dir": "eval/corpus/fuzz-invariant", "contract": "src/Fuzz.sol",
         "cls": "invariant", "loc": "inc", "poc": None,
         "impact": "a sequence of inc() calls flips an invariant that must always hold"},
    ]
    out = []
    for c in CORPUS:
        p = os.path.join(ROOT, c["dir"], c["contract"])
        if not os.path.exists(p):
            continue
        src = _norm(open(p).read())
        sha = _sha(src)
        out.append(Example("A", c["cls"],
                           "Analyze this Solidity contract for security vulnerabilities. Name the "
                           "vulnerability class and the function, and explain the root cause.",
                           src, f"Vulnerability: {c['cls']} in {c['loc']}().\nRoot cause: {c['impact']}.",
                           "seclab-corpus", "proprietary-internal", sha))
        if c["poc"]:
            pocp = os.path.join(ROOT, c["dir"], c["poc"])
            if os.path.exists(pocp):
                out.append(Example("C", c["cls"],
                                   f"Write a self-contained Foundry PoC test that demonstrates the "
                                   f"{c['cls']} in {c['loc']}(). Seed victim funds and assert net theft.",
                                   src, _norm(open(pocp).read()),
                                   "seclab-corpus", "proprietary-internal", sha))
    return out


def load_smartbugs(base: str) -> list[Example]:
    vj = os.path.join(base, "vulnerabilities.json")
    if not os.path.exists(vj):
        return []
    entries = json.load(open(vj))
    out = []
    for e in entries:
        fp = os.path.join(base, e["path"])
        if not os.path.exists(fp):
            continue
        src = _norm(open(fp, errors="ignore").read())
        if len(src) > 24000:
            continue
        sha = _sha(src)
        vulns = e.get("vulnerabilities", [])
        cls = (vulns[0].get("category") if vulns else None) or e["path"].split("/")[-2]
        lines = sorted({l for v in vulns for l in v.get("lines", [])})
        loc = f"around line(s) {', '.join(map(str, lines[:6]))}" if lines else "in the contract"
        expl = CLASS_EXPLAIN.get(cls, "a security-relevant issue")
        out.append(Example("A", cls,
                           "Analyze this Solidity contract for security vulnerabilities. Name the "
                           "vulnerability class and where it occurs, and explain the root cause.",
                           src, f"Vulnerability: {cls} {loc}.\nRoot cause: {expl}.",
                           "smartbugs-curated", "Apache-2.0", sha))
    return out


LOADERS = {
    "corpus": lambda: load_corpus(),
    "smartbugs": lambda: load_smartbugs(os.path.join(SCRATCH, "datasets", "smartbugs-curated")),
}


# ---------------- curation ----------------

def split_for(contract_sha: str) -> str:
    b = int(contract_sha[:8], 16) % 100
    return "train" if b < 70 else ("val" if b < 85 else "test")


def curate(sources: list[str]):
    seen_example = set()
    examples: list[Example] = []
    per_source = {}
    for name in sources:
        loaded = LOADERS[name]()
        per_source[name] = len(loaded)
        for ex in loaded:
            key = (ex.contract_sha, ex.capability, _sha(ex.output)[:16])
            if key in seen_example:
                continue
            seen_example.add(key)
            ex.split = split_for(ex.contract_sha)
            examples.append(ex)
    return examples, per_source


def write(examples: list[Example], out_dir: str, per_source: dict):
    os.makedirs(out_dir, exist_ok=True)
    splits = {"train": [], "val": [], "test": []}
    for ex in examples:
        splits[ex.split].append(ex)
    for name, rows in splits.items():
        with open(os.path.join(out_dir, f"{name}.jsonl"), "w") as f:
            for ex in rows:
                f.write(json.dumps(asdict(ex)) + "\n")
    def dist(key):
        d = {}
        for ex in examples:
            k = getattr(ex, key)
            d[k] = d.get(k, 0) + 1
        return dict(sorted(d.items(), key=lambda x: -x[1]))
    card = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total": len(examples),
        "splits": {k: len(v) for k, v in splits.items()},
        "by_capability": dist("capability"),
        "by_class": dist("vuln_class"),
        "sources_loaded": per_source,
        "licenses": sorted({ex.license for ex in examples}),
        "unique_contracts": len({ex.contract_sha for ex in examples}),
        "dataset_hash": _sha("".join(sorted(ex.contract_sha for ex in examples))),
        "leakage_control": "split assigned per contract_sha; no contract spans splits",
    }
    with open(os.path.join(out_dir, "data_card.json"), "w") as f:
        json.dump(card, f, indent=2)
    return card


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", nargs="+", default=["corpus", "smartbugs"])
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "training", "data"))
    a = ap.parse_args()
    examples, per_source = curate(a.sources)
    card = write(examples, a.out_dir, per_source)
    # leakage assertion
    by_contract = {}
    for ex in examples:
        by_contract.setdefault(ex.contract_sha, set()).add(ex.split)
    assert all(len(s) == 1 for s in by_contract.values()), "LEAKAGE: a contract spans splits"
    print(json.dumps(card, indent=2))


if __name__ == "__main__":
    main()
