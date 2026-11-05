"""Live-target ingestion: fetch verified source (Sourcify V2) for a deployed contract
and materialize a compilable Foundry project. PoCs run against an Anvil fork only."""
from __future__ import annotations
import json, os, re, urllib.request


def fetch_sourcify(address: str, chain: int = 1, timeout: int = 40) -> dict | None:
    url = (f"https://sourcify.dev/server/v2/contract/{chain}/{address}"
           "?fields=sources,metadata,compilation")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            d = json.loads(r.read())
    except Exception:
        return None
    return d if d.get("sources") else None


def solc_version(d: dict) -> str:
    for v in ((d.get("metadata") or {}).get("compiler") or {}).get("version", ""), \
             (d.get("compilation") or {}).get("compilerVersion", ""), \
             (d.get("compilation") or {}).get("fullVersion", ""):
        m = re.match(r"v?(\d+\.\d+\.\d+)", v or "")
        if m:
            return m.group(1)
    return "0.8.20"


def main_contract(d: dict) -> str | None:
    comp = d.get("compilation") or {}
    if comp.get("name"):
        return comp["name"]
    tgt = ((d.get("metadata") or {}).get("settings") or {}).get("compilationTarget") or {}
    for _path, name in tgt.items():
        return name
    return None


def materialize(d: dict, dest: str) -> dict:
    os.makedirs(dest, exist_ok=True)
    nfiles = 0
    for path, obj in d["sources"].items():
        content = obj.get("content", "") if isinstance(obj, dict) else str(obj)
        safe = path.lstrip("/").replace("..", "_")
        fp = os.path.join(dest, safe)
        os.makedirs(os.path.dirname(fp) or dest, exist_ok=True)
        with open(fp, "w") as fh:
            fh.write(content)
        nfiles += 1
    solc = solc_version(d)
    settings = ((d.get("metadata") or {}).get("settings") or {})
    remaps = settings.get("remappings") or []
    opt = settings.get("optimizer") or {}
    optimizer = bool(opt.get("enabled", True))
    runs = int(opt.get("runs", 200))
    via_ir = bool(settings.get("viaIR", False))
    evm = settings.get("evmVersion")
    toml = ('[profile.default]\nsrc = "."\ntest = "__none__"\nout = "out"\n'
            f'solc = "{solc}"\nauto_detect_remappings = true\n'
            f'optimizer = {str(optimizer).lower()}\noptimizer_runs = {runs}\n'
            f'via_ir = {str(via_ir).lower()}\n')
    if evm:
        toml += f'evm_version = "{evm}"\n'
    if remaps:
        toml += "remappings = [" + ", ".join(f'"{r}"' for r in remaps) + "]\n"
    with open(os.path.join(dest, "foundry.toml"), "w") as fh:
        fh.write(toml)
    return {"solc": solc, "nfiles": nfiles, "main": main_contract(d), "remappings": remaps}


def ingest_onchain(address: str, chain: int, dest: str) -> dict | None:
    d = fetch_sourcify(address, chain)
    if not d:
        return None
    info = materialize(d, dest)
    info.update({"address": address, "chain": chain, "target_dir": dest})
    return info
