"""Self-labeling flywheel: run the lab's own Slither over a large raw-contract corpus to
generate capability-A examples at scale. Time-bounded + parallel. Emits JSONL the data
pipeline ingests (load_slither_wild). Scales to any contract corpus (SmartBugs-wild,
Sourcify dumps, etc.)."""
from __future__ import annotations
import argparse, glob, json, os, random, subprocess, time
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRATCH = os.environ.get("SECLAB_SCRATCH", "/opt/dlami/nvme/seclab")
IMG = "seclab-web3/analysis:latest"
FAMILY = {"reentrancy-eth": "reentrancy", "reentrancy-no-eth": "reentrancy",
          "arbitrary-send-eth": "unprotected-ether-withdrawal", "suicidal": "unprotected-selfdestruct",
          "tx-origin": "access_control", "unchecked-transfer": "unchecked_low_level_calls",
          "unchecked-lowlevel": "unchecked_low_level_calls", "weak-prng": "bad_randomness",
          "controlled-delegatecall": "delegatecall", "timestamp": "time_manipulation"}


def slither_label(path: str, timeout: int = 40):
    d = os.path.dirname(os.path.abspath(path))
    fn = os.path.basename(path)
    cmd = ["docker", "run", "--rm", "--network", "none", "-e", "HOME=/cache",
           "-v", f"{SCRATCH}/toolcache:/cache", "-v", f"{d}:/work", "-w", "/work", IMG,
           "bash", "-c", f"slither {fn} --json - 2>/dev/null"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
        data = json.loads(out)
    except Exception:
        return None
    dets = (data.get("results") or {}).get("detectors", [])
    hi = [d for d in dets if d.get("impact") in ("High", "Medium")]
    if not hi:
        return None
    classes = sorted({FAMILY.get(d.get("check"), d.get("check")) for d in hi})
    return classes[:4]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=os.path.join(SCRATCH, "datasets", "smartbugs-wild"))
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--budget-min", type=int, default=45)
    ap.add_argument("--out", default="training/data/slither_wild.jsonl")
    a = ap.parse_args()
    files = glob.glob(os.path.join(a.corpus, "**", "*.sol"), recursive=True)
    random.Random(0).shuffle(files)
    files = files[:a.n]
    print(f"harvesting from {len(files)} contracts, budget {a.budget_min}min, workers {a.workers}")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    deadline = time.time() + a.budget_min * 60
    kept = 0
    with open(a.out, "w") as fh, ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(slither_label, f): f for f in files}
        for fut in as_completed(futs):
            if time.time() > deadline:
                break
            f = futs[fut]
            try:
                classes = fut.result()
            except Exception:
                classes = None
            if not classes:
                continue
            try:
                src = open(f, errors="ignore").read().strip()
            except Exception:
                continue
            if len(src) < 150 or len(src) > 24000:
                continue
            fh.write(json.dumps({"src": src, "classes": classes}) + "\n")
            fh.flush()
            kept += 1
            if kept % 25 == 0:
                print(f"  kept {kept}...", flush=True)
    print(f"done: {kept} labeled examples -> {a.out}")


if __name__ == "__main__":
    main()
