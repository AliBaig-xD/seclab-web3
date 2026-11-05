"""seclab-web3 CLI. `python3 -m orchestrator.cli scan <target_dir> ...`"""
from __future__ import annotations
import argparse, os, time
from .authorization import ScopeGate
from .evidence import EvidenceStore
from .pipeline import Pipeline
from .tools.slither import SlitherScanner
from .tools.aderyn import AderynScanner
from .tools.semgrep import SemgrepScanner
from .tools.mythril import MythrilScanner
from .tools.foundry import FoundryPoCVerifier
from .report import render_markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="seclab-web3")
    ap.add_argument("cmd", choices=["scan"])
    ap.add_argument("target")
    ap.add_argument("--target-id")
    ap.add_argument("--poc-test")
    ap.add_argument("--poc-family", default="reentrancy")
    ap.add_argument("--run-id")
    ap.add_argument("--report")
    ap.add_argument("--llm", action="store_true", help="enable live LLM researcher")
    ap.add_argument("--fast", action="store_true", help="skip slow symbolic/fuzz engines")
    a = ap.parse_args(argv)

    os.chdir(ROOT)
    target = os.path.abspath(a.target)
    tid = a.target_id or os.path.basename(target.rstrip("/"))

    gate = ScopeGate(os.path.join(ROOT, "config", "authorization.yaml"))
    rec = gate.assert_authorized(tid, poc=bool(a.poc_test))
    print(f"[auth] {tid}: basis={rec.get('basis')} poc={bool(a.poc_test)} OK")

    os.makedirs("results", exist_ok=True)
    store = EvidenceStore("results/evidence.db")
    scanners = [SlitherScanner(), AderynScanner(), SemgrepScanner()]
    if not a.fast:
        scanners.append(MythrilScanner())
    verifiers = []
    if a.poc_test:
        verifiers.append(FoundryPoCVerifier(a.poc_test, a.poc_family))

    researcher = None
    llm_code = None
    if a.llm:
        from .model_client import OllamaClient
        from .researcher import Researcher
        from .config import load_model_config
        from .ingest import read_sources
        mc = load_model_config()
        client = OllamaClient(mc["endpoint"], mc["model_ref"], mc.get("params"))
        if client.available():
            researcher = Researcher(client)
            llm_code = read_sources(target)
            print(f"[llm] researcher enabled ({mc['model_ref']}), {len(llm_code)} chars of source")
        else:
            print("[llm] model endpoint unavailable; proceeding static-only")

    run_id = a.run_id or f"run-{int(time.time())}"
    print(f"[run] {run_id} scanning {target}")
    findings = Pipeline(store, scanners, verifiers,
                        researcher=researcher, llm_code=llm_code).run(run_id, target, tid)

    md = render_markdown({"target": tid, "run_id": run_id}, findings)
    out = a.report or f"results/report-{run_id}.md"
    with open(out, "w") as fh:
        fh.write(md)
    rep = sum(1 for f in findings if f.reportable)
    proven = sum(1 for f in findings if f.tier.value == "PROVEN")
    print(f"[done] findings={len(findings)} reportable={rep} proven={proven}")
    print(f"[report] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
