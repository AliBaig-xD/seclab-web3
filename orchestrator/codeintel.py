"""Code intelligence: call graph, reachability, roles, state maps, and deterministic
interaction pairs. Foundation for graph-based slicing (Phase 9 swarm engine)."""
from __future__ import annotations
import json, os, subprocess
from .tools.base import IMAGE, SCRATCH, DOCKER_SAFE

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analysis", "scripts")
PRIV_HINTS = ("only", "auth", "admin", "owner", "governance", "restricted")


def extract(target_dir: str, timeout: int = 600) -> dict:
    cache = f"{SCRATCH}/toolcache"
    os.makedirs(cache, exist_ok=True)
    cmd = ["docker", "run", "--rm", *DOCKER_SAFE, "-e", "HOME=/cache", "-v", f"{cache}:/cache",
           "-v", f"{SCRIPTS_DIR}:/scripts:ro", "-v", f"{target_dir}:/work", "-w", "/work",
           IMAGE, "bash", "-c", "python3 -I /scripts/codeintel_extract.py 2>/dev/null"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return json.loads(p.stdout)
    except Exception:
        return {"contracts": []}


# ---------- pure graph logic (unit-tested, no docker) ----------

def functions(model: dict):
    """Yield (contract, func_dict)."""
    for c in model.get("contracts", []):
        for f in c.get("functions", []):
            yield c["contract"], f


def call_graph(model: dict) -> dict:
    """{(contract, func): [(contract, callee), ...]} resolved within the contract."""
    names = {}
    for cname, f in functions(model):
        names.setdefault(cname, set()).add(f["name"])
    g = {}
    for cname, f in functions(model):
        g[(cname, f["name"])] = [(cname, cal) for cal in f.get("calls", [])
                                 if cal in names.get(cname, set())]
    return g


def entrypoints(model: dict):
    return [(c, f["name"]) for c, f in functions(model)
            if f.get("vis") in ("public", "external")]


def reachable(graph: dict, start) -> set:
    seen, stack = set(), [start]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(graph.get(n, []))
    return seen


def is_privileged(f: dict) -> bool:
    return any(any(h in m.lower() for h in PRIV_HINTS) for m in f.get("modifiers", []))


def interaction_pairs(model: dict):
    """Deterministic seed for cross-slice re-hypothesis: (A, B, shared_state) where A
    WRITES state that B reads or writes. These are the A-then-B interaction candidates."""
    fns = [(c, f) for c, f in functions(model)]
    pairs = []
    for ca, fa in fns:
        wa = set(fa.get("writes", []))
        if not wa:
            continue
        for cb, fb in fns:
            if (ca, fa["name"]) == (cb, fb["name"]):
                continue
            shared = wa & (set(fb.get("reads", [])) | set(fb.get("writes", [])))
            if shared:
                pairs.append(((ca, fa["name"]), (cb, fb["name"]), sorted(shared)))
    return pairs


def build_slices(model: dict) -> list:
    """One slice per external entrypoint: the entry + transitively reachable functions,
    the state they touch, and the roles that gate them."""
    g = call_graph(model)
    byname = {(c, f["name"]): f for c, f in functions(model)}
    slices = []
    for ep in entrypoints(model):
        members = reachable(g, ep)
        state, roles = set(), set()
        for m in members:
            f = byname.get(m)
            if not f:
                continue
            state |= set(f.get("reads", [])) | set(f.get("writes", []))
            roles |= set(f.get("modifiers", []))
        entry_f = byname.get(ep, {})
        slices.append({
            "id": f"{ep[0]}.{ep[1]}",
            "contract": ep[0], "entry": ep[1],
            "functions": sorted(f"{c}.{n}" for c, n in members),
            "state": sorted(state), "roles": sorted(roles),
            "privileged": is_privileged(entry_f),
            "payable": bool(entry_f.get("payable")),
            "low_level": bool(entry_f.get("low_level")),
        })
    return slices
