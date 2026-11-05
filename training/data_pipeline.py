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




def load_solidifi(base: str) -> list[Example]:
    import csv
    bc = os.path.join(base, "buggy_contracts")
    res = os.path.join(base, "results")
    CLS = {"Overflow-Underflow": "arithmetic", "Re-entrancy": "reentrancy", "TOD": "front_running",
           "Timestamp-Dependency": "time_manipulation", "Unchecked-Send": "unchecked_low_level_calls",
           "Unhandled-Exceptions": "unchecked_low_level_calls", "tx.origin": "access_control"}
    out = []
    if not os.path.isdir(bc):
        return out
    for bug_dir in sorted(os.listdir(bc)):
        cls = CLS.get(bug_dir, bug_dir.lower())
        for f in sorted(glob.glob(os.path.join(bc, bug_dir, "*.sol"))):
            try:
                src = _norm(open(f, errors="ignore").read())
            except Exception:
                continue
            if len(src) < 200 or len(src) > 24000:
                continue
            idx = re.search(r"(\d+)", os.path.basename(f))
            lines = []
            if idx:
                log = os.path.join(res, bug_dir, f"BugLog_{idx.group(1)}.csv")
                if os.path.exists(log):
                    try:
                        for row in csv.DictReader(open(log)):
                            loc = (row.get("loc") or "").strip()
                            if loc.isdigit():
                                lines.append(int(loc))
                    except Exception:
                        pass
            lines = sorted(set(lines))[:8]
            loc = f"around line(s) {', '.join(map(str, lines))}" if lines else "in the contract"
            out.append(Example("A", cls,
                               "Analyze this Solidity contract for security vulnerabilities. Name the "
                               "vulnerability class and where it occurs, and explain the root cause.",
                               src, f"Vulnerability: {cls} {loc}.\nRoot cause: {CLASS_EXPLAIN.get(cls, 'a security-relevant issue')}.",
                               "solidifi", "mixed-public-etherscan", _sha(src)))
    return out


def load_not_so_smart(base: str) -> list[Example]:
    out = []
    for d in sorted(glob.glob(os.path.join(base, "*"))):
        if not os.path.isdir(d):
            continue
        cls = os.path.basename(d).lower()
        readme = os.path.join(d, "README.md")
        expl = ""
        if os.path.exists(readme):
            expl = re.sub(r"[#*`>|\[\]()]", " ", open(readme, errors="ignore").read())
            expl = re.sub(r"\s+", " ", expl).strip()[:600]
        for f in glob.glob(os.path.join(d, "**", "*.sol"), recursive=True):
            try:
                src = _norm(open(f, errors="ignore").read())
            except Exception:
                continue
            if len(src) < 150 or len(src) > 24000:
                continue
            out.append(Example("A", cls,
                               "Analyze this Solidity contract for security vulnerabilities and explain the "
                               "root cause and how to exploit it.",
                               src, f"Vulnerability class: {cls}.\n{expl}" if expl else f"Vulnerability class: {cls}.",
                               "not-so-smart-contracts", "Apache-2.0", _sha(src)))
    return out


def load_defihacklabs(base: str) -> list[Example]:
    out = []
    for f in sorted(glob.glob(os.path.join(base, "src", "test", "**", "*.sol"), recursive=True)):
        try:
            poc = open(f, errors="ignore").read()
        except Exception:
            continue
        if "is Test" not in poc or len(poc) > 16000 or len(poc) < 400:
            continue
        name = re.sub(r"[_-]?exp(loit)?\.(t\.)?sol$", "", os.path.basename(f), flags=re.I)
        name = name.replace("_", " ").strip() or "the"
        ref = ""
        m = re.search(r"https?://\S+", poc)
        if m:
            ref = f" Reference: {m.group(0).rstrip('*/ ')}"
        out.append(Example("C", "exploit-poc",
                           f"Write a Foundry PoC test that reproduces the {name} exploit.{ref}",
                           "", _norm(poc),
                           "DeFiHackLabs", "Apache-2.0", _sha(poc)))
    return out


def load_web3bugs(base: str) -> list[Example]:
    import csv
    f = os.path.join(base, "results", "bugs.csv")
    if not os.path.exists(f):
        return []
    out = []
    KW = {"reentran": "reentrancy", "oracle": "oracle-manipulation", "access": "access_control",
          "overflow": "arithmetic", "underflow": "arithmetic", "rounding": "arithmetic",
          "flash": "flash-loan", "signature": "signature-replay", "delegatecall": "delegatecall",
          "slippage": "front_running", "liquidat": "defi-liquidation"}
    for row in csv.DictReader(open(f)):
        desc = (row.get(" Bug Description") or row.get("Bug Description") or "").strip().strip('"')
        if len(desc) < 25:
            continue
        ref = (row.get(" Reference") or "").strip()
        bid = (row.get(" Bug ID") or "?").strip()
        cls = next((v for k, v in KW.items() if k in desc.lower()), "audit-finding")
        out.append(Example("B", cls,
                           "A security auditor reported the following finding in a DeFi protocol. Explain the "
                           "vulnerability class, the mechanism, and why it is serious.",
                           f"Finding {bid}: {desc}",
                           f"This is a {cls} issue. {desc}" + (f" (Reference: {ref})" if ref else ""),
                           "Web3Bugs", "MIT", _sha(bid + desc)))
    return out


def load_defivulnlabs(base: str) -> list[Example]:
    out = []
    import re as _re
    NAME = {"reentrancy":"reentrancy","txorigin":"access_control","overflow":"arithmetic",
            "underflow":"arithmetic","delegatecall":"delegatecall","selfdestruct":"unprotected-selfdestruct",
            "randomness":"bad_randomness","signature":"signature-replay","approval":"access_control"}
    for f in glob.glob(os.path.join(base, "src", "test", "*.sol")):
        try:
            src = open(f, errors="ignore").read()
        except Exception:
            continue
        if len(src) < 150 or len(src) > 20000:
            continue
        stem = os.path.basename(f).replace(".sol", "").lower()
        cls = next((v for k, v in NAME.items() if k in stem), stem)
        cmts = " ".join(_re.findall(r"//\s*(.+)", src)[:12])
        cmts = _re.sub(r"\s+", " ", cmts)[:500]
        out.append(Example("A", cls,
                           "Analyze this Solidity code. Identify the vulnerability pattern it demonstrates "
                           "and explain the root cause and exploitation.",
                           _norm(src),
                           f"Vulnerability pattern: {cls}. {cmts}" if cmts else f"Vulnerability pattern: {cls}.",
                           "DeFiVulnLabs", "unknown-public", _sha(src)))
    return out


def load_verified(path: str) -> list[Example]:
    out = []
    if not os.path.exists(path):
        return out
    for line in open(path):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if not (r.get("input") and r.get("output")):
            continue
        out.append(Example(r.get("capability", "A"), r.get("vuln_class", "unknown"),
                           r["instruction"], _norm(r["input"]), r["output"],
                           r.get("source", "verified-flywheel"),
                           r.get("license", "proprietary-internal"), _sha(_norm(r["input"]))))
    return out


LOADERS = {
    "corpus": lambda: load_corpus(),
    "smartbugs": lambda: load_smartbugs(os.path.join(SCRATCH, "datasets", "smartbugs-curated")),
    "solidifi": lambda: load_solidifi(os.path.join(SCRATCH, "datasets", "solidifi")),
    "not_so_smart": lambda: load_not_so_smart(os.path.join(SCRATCH, "datasets", "not-so-smart")),
    "defihacklabs": lambda: load_defihacklabs(os.path.join(SCRATCH, "datasets", "defihacklabs")),
}


def load_slither_wild(path: str) -> list[Example]:
    out = []
    if not os.path.exists(path):
        return out
    for line in open(path):
        try:
            r = json.loads(line)
        except Exception:
            continue
        src = _norm(r.get("src", ""))
        classes = r.get("classes", [])
        if not src or not classes:
            continue
        cls = classes[0]
        out.append(Example("A", cls,
                           "Analyze this Solidity contract for security vulnerabilities. List the "
                           "vulnerability classes you find.",
                           src, "Vulnerabilities: " + ", ".join(classes) + ".",
                           "slither-wild (self-labeled)", "mixed-public", _sha(src)))
    return out


LOADERS["web3bugs"] = lambda: load_web3bugs(os.path.join(SCRATCH, "datasets", "web3bugs"))
LOADERS["slither_wild"] = lambda: load_slither_wild(os.path.join(ROOT, "training", "data", "slither_wild.jsonl"))
LOADERS["defivulnlabs"] = lambda: load_defivulnlabs(os.path.join(SCRATCH, "datasets", "defivulnlabs"))
LOADERS["verified"] = lambda: load_verified(os.path.join(ROOT, "training", "data", "verified.jsonl"))


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
    ap.add_argument("--sources", nargs="+", default=["corpus","smartbugs","solidifi","not_so_smart","defihacklabs","web3bugs","defivulnlabs","slither_wild","verified"])
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
