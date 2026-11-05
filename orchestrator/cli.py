"""seclab — production CLI for the EVM security research harness.

  seclab scan <dir> [engine flags]
  seclab onchain <0xaddr> --chain <id> --basis <own|bounty:x|engagement:y> [engine flags]
  seclab benchmark [--fast]        seclab kg <dir>
  seclab doctor                    seclab train [--dry]      seclab harvest
"""
from __future__ import annotations
import argparse, json, os, sys
from .harness import ResearchHarness, ScanOptions

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
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--run-id")
    p.add_argument("--target-id")


def cmd_scan(a):
    r = ResearchHarness().run(local=a.target, opt=_opts(a), target_id=a.target_id, run_id=a.run_id)
    return 2 if "error" in r else 0


def cmd_onchain(a):
    r = ResearchHarness().run(onchain=a.address, chain=a.chain, basis=a.basis,
                              opt=_opts(a), target_id=a.target_id, run_id=a.run_id)
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


def cmd_harvest(a):
    os.execvp("bash", ["bash", os.path.join(ROOT, "scripts", "run_harvest.sh")])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="seclab", description="EVM security research harness")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="scan a local target directory")
    s.add_argument("target")
    _add_engine_flags(s)
    s.set_defaults(fn=cmd_scan)
    o = sub.add_parser("onchain", help="scan a deployed verified contract")
    o.add_argument("address")
    o.add_argument("--chain", type=int, default=1)
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
    sub.add_parser("harvest", help="self-label raw contracts to grow the dataset").set_defaults(fn=cmd_harvest)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
