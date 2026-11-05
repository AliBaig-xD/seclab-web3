"""Runs INSIDE the analysis container. Extracts code intelligence via the Slither API:
per-function visibility, modifiers, state reads/writes, internal/external calls."""
import json, os, sys

# never let a sibling file shadow the real slither package
sys.path = [p for p in sys.path if os.path.abspath(p or ".") != os.path.dirname(os.path.abspath(__file__))]
from slither import Slither


def _callees(f):
    out = []
    for ic in getattr(f, "internal_calls", []) or []:
        fn = getattr(ic, "function", ic)
        nm = getattr(fn, "name", None)
        if nm and "Solidity" not in type(fn).__name__:
            out.append(nm)
    return sorted(set(out))


def _ext_calls(f):
    out = []
    for hc in getattr(f, "high_level_calls", []) or []:
        tgt = hc[1] if isinstance(hc, (list, tuple)) and len(hc) > 1 else hc
        nm = getattr(tgt, "name", None)
        if nm:
            out.append(nm)
    return sorted(set(out))


def main(path="."):
    sl = Slither(path)
    contracts = []
    for c in sl.contracts:
        if getattr(c, "is_interface", False):
            continue
        funcs = []
        for f in c.functions_declared:
            try:
                reads = sorted({v.name for v in f.state_variables_read if getattr(v, "name", None)})
                writes = sorted({v.name for v in f.state_variables_written if getattr(v, "name", None)})
            except Exception:
                reads, writes = [], []
            funcs.append({
                "name": f.name, "sig": f.full_name, "vis": str(f.visibility),
                "modifiers": [m.name for m in f.modifiers],
                "reads": reads, "writes": writes,
                "calls": _callees(f), "external_calls": _ext_calls(f),
                "payable": bool(getattr(f, "payable", False)),
                "low_level": bool(getattr(f, "low_level_calls", [])),
            })
        try:
            svars = [v.name for v in c.state_variables_ordered if getattr(v, "name", None)]
        except Exception:
            svars = []
        contracts.append({"contract": c.name,
                          "inherits": [x.name for x in c.inheritance],
                          "state_vars": svars, "functions": funcs})
    print(json.dumps({"contracts": contracts}))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
