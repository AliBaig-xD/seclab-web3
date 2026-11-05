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


# ---- target harvesting: pull candidate contracts so you don't hand-pick ----
import os as _os, json as _json, time as _time, urllib.request as _ur, datetime as _dt


def _get_json(url, timeout=30):
    req = _ur.Request(url, headers={"User-Agent": "seclab-web3"})
    with _ur.urlopen(req, timeout=timeout) as r:
        return _json.load(r)


def _epoch(d):  # 'YYYY-MM-DD' -> unix seconds (UTC)
    return int(_dt.datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=_dt.timezone.utc).timestamp())


def _deploy_ts(chain, addr, key):
    """Deployment timestamp via Etherscan v2; None if unknown."""
    try:
        u = (f"https://api.etherscan.io/v2/api?chainid={chain}&module=contract"
             f"&action=getcontractcreation&contractaddresses={addr}&apikey={key}")
        r = _get_json(u).get("result")
        if not isinstance(r, list) or not r:
            return None
        if r[0].get("timestamp"):
            return int(r[0]["timestamp"])
        bn = r[0].get("blockNumber")
        if not bn:
            return None
        u2 = (f"https://api.etherscan.io/v2/api?chainid={chain}&module=block"
              f"&action=getblockreward&blockno={bn}&apikey={key}")
        return int(_get_json(u2)["result"]["timeStamp"])
    except Exception:
        return None


def harvest_targets(chain=1, limit=100, sort="desc", before=None, after=None,
                    out=None, log=print):
    """Harvest verified-contract addresses (Sourcify bulk index). Optional deploy-date
    window (before/after = 'YYYY-MM-DD') filters via Etherscan — needs ETHERSCAN_API_KEY.
    Writes a targets file ready for `seclab batch`."""
    key = _os.environ.get("ETHERSCAN_API_KEY", "")
    date_filter = bool(before or after)
    if date_filter and not key:
        log("[warn] date filter needs ETHERSCAN_API_KEY; harvesting without date filter")
        date_filter = False
    lo = _epoch(after) if after else None
    hi = _epoch(before) if before else None
    picked, after_id, scanned = [], None, 0
    # when filtering by deploy date we must scan well beyond `limit`
    hard_cap = limit * 60 if date_filter else limit * 2
    while len(picked) < limit and scanned < hard_cap:
        page = min(200, (limit - len(picked)) * (20 if date_filter else 1) + 5)
        url = f"https://sourcify.dev/server/v2/contracts/{chain}?limit={page}&sort={sort}"
        if after_id:
            url += f"&afterMatchId={after_id}"
        res = _get_json(url).get("results", [])
        if not res:
            break
        for row in res:
            scanned += 1
            addr = row.get("address")
            if not addr:
                continue
            if date_filter:
                ts = _deploy_ts(chain, addr, key)
                _time.sleep(0.22)  # free-tier rate limit
                if ts is None or (lo and ts < lo) or (hi and ts >= hi):
                    continue
            picked.append(addr)
            if len(picked) >= limit:
                break
        after_id = res[-1].get("matchId")
        if not after_id:
            break
    if out:
        with open(out, "w") as f:
            win = f" deploy<{before}" if before else ""
            win += f" deploy>={after}" if after else ""
            f.write(f"# {len(picked)} verified contracts chain={chain} sort={sort}{win}\n")
            for a in picked:
                f.write(f"{a} {chain}\n")
        log(f"harvested {len(picked)} targets (scanned {scanned}) -> {out}")
    return picked
