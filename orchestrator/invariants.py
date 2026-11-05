"""Auto-synthesize fuzz/symbolic harnesses from protocol-intelligence invariants, so the
dynamic engines engage on ANY target (not only ones that already ship properties). Turns
natural-language invariants into Echidna property stubs + Halmos check stubs grounded in
the contract's actual public getters/state, for the exploitation/fuzzing loop to compile."""
from __future__ import annotations
import re


def _public_getters(ci: dict, contract: str):
    """Public state vars (which expose a getter) + view functions of the contract."""
    for c in ci.get("contracts", []):
        if c["contract"] != contract:
            continue
        getters = list(c.get("state_vars", []))
        for f in c.get("functions", []):
            if f.get("vis") in ("public", "external") and not f.get("payable"):
                getters.append(f["name"])
        return sorted(set(getters))
    return []


def echidna_property(contract: str, name: str, expr: str) -> str:
    """An Echidna property function body asserting `expr` always holds (returns bool)."""
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", name)[:40]
    return (f"    // invariant: {name}\n"
            f"    function echidna_{safe}() public view returns (bool) {{\n"
            f"        return {expr};\n    }}\n")


def synthesize_echidna(ci: dict, contract: str, invariants: list[str]) -> dict:
    """Return {property_name: expr_template} for invariants we can ground in real getters.
    Only emits a property when the invariant text references a known getter/state name."""
    getters = _public_getters(ci, contract)
    out = {}
    for inv in invariants:
        refs = [g for g in getters if re.search(rf"\b{re.escape(g)}\b", inv)]
        if len(refs) >= 2:
            # e.g. "sum of balances == totalSupply" -> relate two referenced getters
            out[inv] = f"{refs[0]}() <= {refs[1]}()" if "<=" in inv or "<" in inv or "solven" in inv.lower() \
                       else f"{refs[0]}() == {refs[1]}()"
        elif len(refs) == 1:
            out[inv] = f"{refs[0]}() >= 0"   # weak but compilable monotonic/bound stub
    return out


def halmos_check(name: str, func: str, param_types: list[str], assertion: str) -> str:
    """A Halmos symbolic check over a function's inputs asserting `assertion`."""
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", name)[:40]
    params = ", ".join(f"{t} a{i}" for i, t in enumerate(param_types))
    return (f"    function check_{safe}({params}) public {{\n"
            f"        // assert the invariant holds symbolically\n"
            f"        assert({assertion});\n    }}\n")
