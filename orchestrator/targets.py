"""Universal target resolver: accept a raw address, a block-explorer URL (any chain), a
git repo URL, or a local path, and route to the right ingestion path. So the end user can
paste whatever they have."""
from __future__ import annotations
import re, urllib.parse

ADDR = re.compile(r"0x[a-fA-F0-9]{40}")

# block explorer host -> chain id
EXPLORER_CHAINS = {
    "etherscan.io": 1, "sepolia.etherscan.io": 11155111, "holesky.etherscan.io": 17000,
    "arbiscan.io": 42161, "optimistic.etherscan.io": 10, "basescan.org": 8453,
    "polygonscan.com": 137, "bscscan.com": 56, "snowtrace.io": 43114, "snowscan.xyz": 43114,
    "ftmscan.com": 250, "gnosisscan.io": 100, "lineascan.build": 59144,
    "scrollscan.com": 534352, "blastscan.io": 81457, "celoscan.io": 42220,
    "era.zksync.network": 324, "mantlescan.xyz": 5000, "moonscan.io": 1284,
}


def resolve_target(arg: str) -> dict:
    a = (arg or "").strip()
    if ADDR.fullmatch(a):
        return {"kind": "address", "address": a, "chain": None}
    if a.startswith(("http://", "https://")):
        host = urllib.parse.urlparse(a).netloc.lower()
        host = host[4:] if host.startswith("www.") else host
        m = ADDR.search(a)
        if m and (host in EXPLORER_CHAINS or "/address/" in a or "/token/" in a):
            return {"kind": "explorer", "address": m.group(0),
                    "chain": EXPLORER_CHAINS.get(host), "host": host}
        if "github.com" in host or "gitlab.com" in host or "bitbucket.org" in host:
            return {"kind": "repo", "url": a}
        return {"kind": "dapp", "url": a, "host": host}   # a dApp frontend — see note
    if a.endswith(".git") or a.startswith("git@"):
        return {"kind": "repo", "url": a}
    return {"kind": "local", "path": a}
