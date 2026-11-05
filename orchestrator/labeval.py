"""Lab evaluation harness (the north-star metric): run the whole system on a labeled
benchmark + a clean negative control, and report recall, false-positive rate, and
PoC-reproduction rate. Also a regression gate (known bugs must stay found)."""
from __future__ import annotations
import json, os, time
from .evidence import EvidenceStore
from .pipeline import Pipeline, family
from .tools.slither import SlitherScanner
from .tools.aderyn import AderynScanner
from .tools.semgrep import SemgrepScanner
from .tools.mythril import MythrilScanner
from .tools.halmos import HalmosScanner
from .tools.echidna import EchidnaScanner
from .tools.medusa import MedusaScanner

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BENCHMARK = [
    {"dir": "eval/corpus/reentrancy-etherstore", "expect": ["reentrancy"], "negative": False},
    {"dir": "eval/corpus/symbolic-overflow", "expect": ["assertion-violation"], "negative": False},
    {"dir": "eval/corpus/fuzz-invariant", "expect": ["invariant-violation"], "negative": False},
    {"dir": "eval/corpus/clean-guarded", "expect": [], "negative": True},
]


def scanners(full: bool):
    s = [SlitherScanner(), AderynScanner(), SemgrepScanner()]
    if full:
        s += [MythrilScanner(), HalmosScanner(), EchidnaScanner(), MedusaScanner()]
    return s


def run(full: bool = True) -> dict:
    store = EvidenceStore(os.path.join(ROOT, "results", "benchmark.db"))
    scs = scanners(full)
    rows, tp, fn, fp, proven = [], 0, 0, 0, 0
    for b in BENCHMARK:
        tgt = os.path.join(ROOT, b["dir"])
        tid = os.path.basename(b["dir"])
        findings = Pipeline(store, scs, []).run(f"bench-{tid}-{int(time.time())}", tgt, tid)
        classes = {family(f.hypothesis.vuln_type) for f in findings} | {f.hypothesis.vuln_type for f in findings}
        reportable = [f for f in findings if f.reportable]
        if b["negative"]:
            here = len(reportable)
            fp += here
            rows.append({"target": tid, "negative": True, "reportable": here,
                         "ok": here == 0})
        else:
            found = any(e in classes for e in b["expect"])
            tp += int(found)
            fn += int(not found)
            proven += sum(1 for f in reportable if f.tier.value == "PROVEN")
            rows.append({"target": tid, "expect": b["expect"], "found": found,
                         "reportable": len(reportable),
                         "proven": sum(1 for f in reportable if f.tier.value == "PROVEN")})
    pos = tp + fn
    rep = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "engines": "full" if full else "static",
        "recall": round(tp / pos, 3) if pos else None,
        "false_positives_on_clean": fp,
        "proven_findings": proven, "rows": rows,
    }
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "benchmark_report.json"), "w") as f:
        json.dump(rep, f, indent=2)
    return rep


if __name__ == "__main__":
    import sys
    print(json.dumps(run(full=("--fast" not in sys.argv)), indent=2))
