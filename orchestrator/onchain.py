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




def parse_etherscan_source(result0: dict) -> dict | None:
    """Convert an Etherscan getsourcecode result into the Sourcify-shaped dict that
    materialize() consumes. Handles single-file, multi-file standard-json, and the
    double-brace-wrapped variant."""
    raw = (result0.get("SourceCode") or "").strip()
    if not raw:
        return None
    name = result0.get("ContractName") or ""
    sources = {}
    settings = {}
    if raw.startswith("{"):
        body = raw[1:-1] if raw.startswith("{{") and raw.endswith("}}") else raw
        try:
            doc = json.loads(body)
        except Exception:
            doc = None
        if isinstance(doc, dict) and "sources" in doc:
            for path, obj in doc["sources"].items():
                sources[path] = {"content": obj.get("content", "")}
            settings = doc.get("settings", {}) or {}
        elif isinstance(doc, dict):
            for path, obj in doc.items():
                if isinstance(obj, dict) and "content" in obj:
                    sources[path] = {"content": obj["content"]}
    if not sources:
        sources = {f"{name or 'Contract'}.sol": {"content": raw}}
    opt = {"enabled": str(result0.get("OptimizationUsed", "0")) == "1",
           "runs": int(result0.get("Runs", 200) or 200)}
    md = {"compiler": {"version": result0.get("CompilerVersion", "")},
          "settings": {"optimizer": opt, "remappings": settings.get("remappings", []),
                       "viaIR": bool(settings.get("viaIR", False)),
                       "evmVersion": result0.get("EVMVersion") or settings.get("evmVersion")}}
    return {"sources": sources, "metadata": md, "compilation": {"name": name}}


def fetch_etherscan(address: str, chain: int = 1, timeout: int = 40) -> dict | None:
    key = os.environ.get("ETHERSCAN_API_KEY")
    if not key:
        return None
    url = (f"https://api.etherscan.io/v2/api?chainid={chain}&module=contract"
           f"&action=getsourcecode&address={address}&apikey={key}")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            doc = json.loads(r.read())
    except Exception:
        return None
    res = doc.get("result")
    if not isinstance(res, list) or not res:
        return None
    return parse_etherscan_source(res[0])


def ingest_onchain(address: str, chain: int, dest: str) -> dict | None:
    d = fetch_sourcify(address, chain) or fetch_etherscan(address, chain)
    if not d:
        return None
    info = materialize(d, dest)
    info.update({"address": address, "chain": chain, "target_dir": dest})
    return info
