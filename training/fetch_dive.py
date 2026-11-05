"""Fetch a class-balanced, rare-class-weighted subset of DIVE source from Etherscan
(all DIVE contracts are verified). Labels are TOOL-CONSENSUS (not human) -> tagged as such.
Resumable: appends, skips already-fetched addresses."""
import os, csv, json, time, urllib.request, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import orchestrator.config  # loads .env -> ETHERSCAN_API_KEY
KEY = os.environ["ETHERSCAN_API_KEY"]
DIVE = "/opt/dlami/nvme/seclab/datasets/dive"
OUT = "training/data_sources/dive.jsonl"
CLASSES = ["Reentrancy", "Access Control", "Arithmetic", "Unchecked Return Values",
           "DoS", "Bad Randomness", "Front Running", "Time manipulation"]
MAP = {"Reentrancy": "reentrancy", "Access Control": "access_control", "Arithmetic": "arithmetic",
       "Unchecked Return Values": "unchecked_low_level_calls", "DoS": "denial_of_service",
       "Bad Randomness": "bad_randomness", "Front Running": "front_running",
       "Time manipulation": "time_manipulation"}
# rare classes get bigger caps; common classes (we already have plenty) small
CAP = {"bad_randomness": 634, "front_running": 606, "time_manipulation": 800, "denial_of_service": 800,
       "unchecked_low_level_calls": 500, "reentrancy": 450, "arithmetic": 400, "access_control": 350}

addrs = [r[0].strip() for r in csv.reader(open(f"{DIVE}/raw_csv/Raw/DIVE_Samples.csv"))][1:]
labels = {}
for row in csv.DictReader(open(f"{DIVE}/labels/Labels/DIVE_Labels.csv")):
    cid = int(row["contractID"])
    labels[cid] = [MAP[c] for c in CLASSES if (row.get(c) or "").strip() == "1"]

per = Counter(); sel = []
for cid in sorted(labels):
    cls = labels[cid]
    if not cls:
        continue
    if any(per[c] < CAP.get(c, 400) for c in cls):
        sel.append(cid)
        for c in cls:
            per[c] += 1
    if len(sel) >= 5000:
        break
print(f"[dive] selected {len(sel)} contracts; class coverage target {dict(per)}", flush=True)

done = set()
if os.path.exists(OUT):
    for ln in open(OUT):
        try: done.add(json.loads(ln)["address"].lower())
        except: pass
print(f"[dive] resuming; {len(done)} already fetched", flush=True)

def parse_src(s):
    if not s: return ""
    if s.startswith("{{") and s.endswith("}}"):
        try:
            d = json.loads(s[1:-1]); return "\n\n".join(v.get("content", "") for v in d.get("sources", {}).values())
        except Exception: return s
    if s.startswith("{"):
        try:
            d = json.loads(s)
            if "sources" in d: return "\n\n".join(v.get("content", "") for v in d["sources"].values())
        except Exception: pass
    return s

def fetch(addr):
    u = (f"https://api.etherscan.io/v2/api?chainid=1&module=contract&action=getsourcecode"
         f"&address={addr}&apikey={KEY}")
    req = urllib.request.Request(u, headers={"User-Agent": "seclab"})
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.load(r)
    res = d.get("result")
    if not isinstance(res, list) or not res:
        return None
    return parse_src(res[0].get("SourceCode", ""))

out = open(OUT, "a")
n = ok = 0
for cid in sel:
    addr = addrs[cid - 1]
    if addr.lower() in done:
        continue
    n += 1
    try:
        src = fetch(addr)
    except Exception as e:
        src = None
    if src and 200 <= len(src) <= 24000:
        out.write(json.dumps({"address": addr, "classes": labels[cid], "source": src[:24000]}) + "\n")
        out.flush(); ok += 1
    if n % 200 == 0:
        print(f"[dive] fetched {n}, kept {ok}", flush=True)
    time.sleep(0.21)
print(f"[dive] DONE fetched {n}, kept {ok} -> {OUT}", flush=True)
