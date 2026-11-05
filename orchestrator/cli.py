"""seclab — production CLI for the EVM security research harness.

  seclab scan <dir> [engine flags]
  seclab onchain <0xaddr> --chain <id> --basis <own|bounty:x|engagement:y> [engine flags]
  seclab benchmark [--fast]        seclab kg <dir>
  seclab doctor                    seclab train [--dry]      seclab harvest
"""
from __future__ import annotations
import argparse, json, os, sys
from .harness import ResearchHarness, ScanOptions
from .targets import resolve_target, harvest_targets
from .batch import run_batch
from . import config  # noqa: F401  (loads .env)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _opts(a):
    return ScanOptions(llm=a.llm, swarm=a.swarm, rag=a.rag, exploit=a.exploit,
                       differential=a.differential, fast=a.fast, poc_test=a.poc_test,
                       poc_family=a.poc_family, swarm_concurrency=a.swarm_concurrency,
                       verbose=a.verbose)


def _add_engine_flags(p):
    p.add_argument("--llm", action="store_true", help="live LLM researcher + reviewer + protocol intel")
    p.add_argument("--swarm", action="store_true", help="graph-sliced map-reduce hypothesis engine")
    p.add_argument("--rag", action="store_true", help="ground the hunter in the knowledge base")
    p.add_argument("--exploit", action="store_true", help="LLM-generate + run Foundry PoCs")
    p.add_argument("--differential", action="store_true", help="differential testing across solc versions")
    p.add_argument("--fast", action="store_true", help="skip slow symbolic/fuzz engines")
    p.add_argument("--poc-test", help="confirm a known exploit test as PROVEN")
    p.add_argument("--poc-family", default="reentrancy")
    p.add_argument("--swarm-concurrency", type=int, default=1)
    p.add_argument("--thorough", action="store_true", help="multi-sample hypotheses + reviewer voting (more test-time compute)")
    p.add_argument("--parallel", type=int, default=1, help="run analysis engines concurrently (resource-capped)")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--run-id")
    p.add_argument("--target-id")


def cmd_scan(a):
    r = ResearchHarness().run(local=a.target, opt=_opts(a), target_id=a.target_id, run_id=a.run_id)
    return 2 if "error" in r else 0


def cmd_onchain(a):
    t = resolve_target(a.address)
    address = t.get("address", a.address)
    chain = a.chain if a.chain else (t.get("chain") or 1)
    r = ResearchHarness().run(onchain=address, chain=chain, basis=a.basis,
                              opt=_opts(a), target_id=a.target_id, run_id=a.run_id)
    return 2 if "error" in r else 0


def cmd_go(a):
    """Paste anything: address | explorer URL | repo URL | local path."""
    t = resolve_target(a.target)
    k = t["kind"]
    h = ResearchHarness()
    if k in ("address", "explorer"):
        r = h.run(onchain=t["address"], chain=(a.chain or t.get("chain") or 1),
                  basis=a.basis, opt=_opts(a), target_id=a.target_id, run_id=a.run_id)
    elif k == "repo":
        r = h.run(repo=t["url"], basis=a.basis, opt=_opts(a), target_id=a.target_id, run_id=a.run_id)
    elif k == "local":
        r = h.run(local=t["path"], opt=_opts(a), target_id=a.target_id, run_id=a.run_id)
    else:  # dapp
        print(f"[dapp] {t['url']} is a dApp frontend; frontends do not map 1:1 to contracts.")
        print("       Use its GitHub repo (seclab repo <url>) or a deployed address / explorer URL.")
        return 2
    return 2 if "error" in r else 0


def cmd_batch(a):
    flags = []
    for name in ("llm", "swarm", "rag", "exploit", "differential", "fast", "thorough"):
        if getattr(a, name):
            flags.append("--" + name)
    flags += ["--poc-family", a.poc_family, "--swarm-concurrency", str(a.swarm_concurrency),
              "--parallel", str(a.parallel)]
    if a.verbose:
        flags.append("--verbose")
    run_batch(a.file, basis=a.basis, flags=flags, jobs=a.jobs, timeout=a.timeout,
              batch_id=a.batch_id, resume=not a.no_resume)
    return 0


def cmd_targets(a):
    harvest_targets(chain=a.chain, limit=a.limit, sort=a.sort, before=a.before,
                    after=a.after, solc_below=a.solc_below, out=a.out)
    return 0


def cmd_repo(a):
    r = ResearchHarness().run(repo=a.url, basis=a.basis, opt=_opts(a),
                              target_id=a.target_id, run_id=a.run_id)
    return 2 if "error" in r else 0


def cmd_benchmark(a):
    from .labeval import run
    print(json.dumps(run(full=not a.fast), indent=2))
    return 0


def cmd_kg(a):
    from .codeintel import extract
    from .kg import KnowledgeGraph
    g = KnowledgeGraph.from_model(extract(os.path.abspath(a.target)))
    print(json.dumps({"stats": g.stats(),
                      "privileged_functions": g.privileged_functions(),
                      "unguarded_state_writers": g.unguarded_state_writers()}, indent=2))
    return 0


def cmd_doctor(a):
    os.execvp("bash", ["bash", os.path.join(ROOT, "scripts", "doctor.sh")])


def cmd_train(a):
    args = ["bash", os.path.join(ROOT, "scripts", "train.sh")]
    if a.dry:
        args.append("--dry")
    os.execvp("bash", args)


def cmd_dashboard(a):
    from .dashboard import generate
    out, n = generate()
    print(f"dashboard: {out} ({n} runs)")
    return 0


def cmd_harvest(a):
    os.execvp("bash", ["bash", os.path.join(ROOT, "scripts", "run_harvest.sh")])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="seclab", description="EVM security research harness")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="scan a local target directory")
    s.add_argument("target")
    _add_engine_flags(s)
    s.set_defaults(fn=cmd_scan)
    rp = sub.add_parser("repo", help="clone a git repo URL and scan it")
    rp.add_argument("url")
    rp.add_argument("--basis", required=True)
    _add_engine_flags(rp)
    rp.set_defaults(fn=cmd_repo)
    g = sub.add_parser("go", help="paste anything: address | explorer URL | repo URL | local path")
    g.add_argument("target")
    g.add_argument("--chain", type=int, default=0)
    g.add_argument("--basis", default="own")
    _add_engine_flags(g)
    g.set_defaults(fn=cmd_go)
    bt = sub.add_parser("batch", help="scan a list of targets and rank them (leaderboard)")
    bt.add_argument("file", help="targets file: one per line (address | explorer URL | repo | path), '#'=comment, optional ' <chain>'")
    bt.add_argument("--basis", default="own")
    bt.add_argument("--jobs", type=int, default=1, help="targets scanned concurrently (GPU-bound; keep low for --llm)")
    bt.add_argument("--timeout", type=int, default=3600, help="per-target wall timeout (s)")
    bt.add_argument("--batch-id")
    bt.add_argument("--no-resume", action="store_true", help="re-run targets even if a prior run exists")
    _add_engine_flags(bt)
    bt.set_defaults(fn=cmd_batch)
    tg = sub.add_parser("targets", help="harvest a candidate contract list (no hand-picking)")
    tg.add_argument("--chain", type=int, default=1)
    tg.add_argument("--limit", type=int, default=100)
    tg.add_argument("--sort", choices=["desc", "asc"], default="desc", help="by verification time")
    tg.add_argument("--before", help="only contracts DEPLOYED before this date YYYY-MM-DD (needs ETHERSCAN_API_KEY)")
    tg.add_argument("--after", help="only contracts DEPLOYED on/after YYYY-MM-DD")
    tg.add_argument("--solc-below", help="only contracts compiled below this solc (e.g. 0.6.0 ~ pre-2020 era); free, no key; also dedups clones")
    tg.add_argument("--out", required=True, help="write targets file here (feed to `seclab batch`)")
    tg.set_defaults(fn=cmd_targets)
    o = sub.add_parser("onchain", help="scan a deployed verified contract")
    o.add_argument("address")
    o.add_argument("--chain", type=int, default=0)
    o.add_argument("--basis", required=True)
    _add_engine_flags(o)
    o.set_defaults(fn=cmd_onchain)
    b = sub.add_parser("benchmark", help="run the lab benchmark (recall/FP/PoC-repro)")
    b.add_argument("--fast", action="store_true")
    b.set_defaults(fn=cmd_benchmark)
    k = sub.add_parser("kg", help="print the knowledge graph of a target")
    k.add_argument("target")
    k.set_defaults(fn=cmd_kg)
    sub.add_parser("doctor", help="verify the box toolchain").set_defaults(fn=cmd_doctor)
    t = sub.add_parser("train", help="train the specialized model")
    t.add_argument("--dry", action="store_true")
    t.set_defaults(fn=cmd_train)
    sub.add_parser("dashboard", help="generate the static HTML run dashboard").set_defaults(fn=cmd_dashboard)
    sub.add_parser("harvest", help="self-label raw contracts to grow the dataset").set_defaults(fn=cmd_harvest)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
