"""seclab-web3 CLI. `python3 -m orchestrator.cli scan <target_dir> ...`"""
from __future__ import annotations
import argparse, os, subprocess, time
from .authorization import ScopeGate
from .evidence import EvidenceStore
from .pipeline import Pipeline
from .tools.slither import SlitherScanner
from .tools.aderyn import AderynScanner
from .tools.semgrep import SemgrepScanner
from .tools.mythril import MythrilScanner
from .tools.halmos import HalmosScanner
from .tools.echidna import EchidnaScanner
from .tools.medusa import MedusaScanner
from .tools.foundry import FoundryPoCVerifier
from .report import render_markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="seclab-web3")
    ap.add_argument("cmd", choices=["scan"])
    ap.add_argument("target", nargs="?")
    ap.add_argument("--onchain", help="deployed address to ingest via Sourcify")
    ap.add_argument("--chain", type=int, default=1)
    ap.add_argument("--basis", help="authorization basis for on-chain: own|bounty:<p>|engagement:<id>")
    ap.add_argument("--target-id")
    ap.add_argument("--poc-test")
    ap.add_argument("--poc-family", default="reentrancy")
    ap.add_argument("--run-id")
    ap.add_argument("--report")
    ap.add_argument("--llm", action="store_true", help="enable live LLM researcher")
    ap.add_argument("--fast", action="store_true", help="skip slow symbolic/fuzz engines")
    ap.add_argument("--swarm", action="store_true", help="graph-sliced map-reduce hypothesis engine")
    ap.add_argument("--swarm-concurrency", type=int, default=1)
    ap.add_argument("--exploit", action="store_true", help="LLM-generate+run Foundry PoCs to prove candidates")
    ap.add_argument("--rag", action="store_true", help="ground the hunter in the vuln knowledge base")
    ap.add_argument("--kg", action="store_true", help="build + save a knowledge graph of the target")
    ap.add_argument("--differential", action="store_true", help="run differential testing across solc versions")
    a = ap.parse_args(argv)

    os.chdir(ROOT)
    if a.onchain:
        from .onchain import ingest_onchain
        import os as _os
        scratch = _os.environ.get("SECLAB_SCRATCH", "/opt/dlami/nvme/seclab")
        addr = a.onchain
        target = f"{scratch}/onchain-{addr.lower()}"
        subprocess.run(["sudo", "rm", "-rf", target])
        info = ingest_onchain(addr, a.chain, target)
        if not info:
            print(f"[onchain] no verified source for {addr} on chain {a.chain}")
            return 2
        tid = a.target_id or addr.lower()
        print(f"[onchain] ingested {addr}: solc={info['solc']} files={info['nfiles']} main={info['main']}")
        if not a.basis:
            print("[auth] on-chain target requires --basis (own|bounty:<p>|engagement:<id>)")
            return 2
        gate = ScopeGate.ephemeral(tid, a.basis, poc_allowed=bool(a.poc_test),
                                   affirmed_by="dev@archrco.com")
    else:
        target = os.path.abspath(a.target)
        tid = a.target_id or os.path.basename(target.rstrip("/"))
        gate = ScopeGate(os.path.join(ROOT, "config", "authorization.yaml"))
    rec = gate.assert_authorized(tid, poc=bool(a.poc_test))
    print(f"[auth] {tid}: basis={rec.get('basis')} poc={bool(a.poc_test)} OK")

    os.makedirs("results", exist_ok=True)
    store = EvidenceStore("results/evidence.db")
    scanners = [SlitherScanner(), AderynScanner(), SemgrepScanner()]
    if a.differential:
        from .tools.differential import DifferentialScanner
        scanners.append(DifferentialScanner())
    if not a.fast:
        scanners.append(MythrilScanner())
        scanners.append(HalmosScanner())
        scanners.append(EchidnaScanner())
        scanners.append(MedusaScanner())
    verifiers = []
    if a.poc_test:
        verifiers.append(FoundryPoCVerifier(a.poc_test, a.poc_family))

    researcher = None
    reviewer = None
    protocol = None
    llm_code = None
    seed = []
    if a.llm or a.swarm:
        from .model_client import OllamaClient
        from .researcher import Researcher
        from .config import load_model_config
        from .ingest import read_sources
        mc = load_model_config()
        client = OllamaClient(mc["endpoint"], mc["model_ref"], mc.get("params"))
        if client.available():
            from .reviewer import LLMReviewer
            from .protocol import ProtocolIntelligence
            kb = None
            if a.rag:
                from .knowledge import KnowledgeBase
                kb = KnowledgeBase(os.path.join(ROOT, "knowledge", "kb.db"))
                if kb.count() == 0:
                    kb.seed_from_cards(os.path.join(ROOT, "knowledge", "cards.json"))
                print(f"[rag] knowledge base: {kb.count()} cards")
            researcher = Researcher(client, kb=kb)
            reviewer = LLMReviewer(client)
            protocol = ProtocolIntelligence(client)
            if a.exploit:
                from .exploit import ExploitationAgent
                globals()["_EXPLOITER"] = ExploitationAgent(client)
            llm_code = read_sources(target)
            print(f"[llm] researcher+reviewer+protocol enabled ({mc['model_ref']}), {len(llm_code)} chars")
            if a.swarm:
                from .codeintel import extract as ci_extract, build_slices, interaction_pairs
                from .swarm import SwarmEngine
                from .ingest import read_source_files, source_for_contract
                ci = ci_extract(target)
                slices = build_slices(ci)
                pairs = interaction_pairs(ci)
                files = read_source_files(target)
                srcs = {c["contract"]: source_for_contract(files, c["contract"])
                        for c in ci.get("contracts", [])}
                pm = protocol.analyze(llm_code)
                eng = SwarmEngine(client, concurrency=a.swarm_concurrency, kb=kb)
                seed = eng.run(slices, pairs, srcs, pm)
                print(f"[swarm] slices={eng.stats['slices']} deep={eng.stats['deep']} "
                      f"pairs={eng.stats['pairs']} hypotheses={len(seed)}")
                researcher = None      # swarm supersedes the single-shot researcher
                protocol = None        # model already computed
                _precomputed_protocol = pm
                globals()["_PRECOMPUTED_PROTOCOL"] = pm
        else:
            print("[llm] model endpoint unavailable; proceeding static-only")

    run_id = a.run_id or f"run-{int(time.time())}"
    print(f"[run] {run_id} scanning {target}")
    from .ingest import read_source_files as _rsf
    pipe = Pipeline(store, scanners, verifiers, reviewer=reviewer,
                    researcher=researcher, llm_code=llm_code, protocol=protocol,
                    seed_hypotheses=seed, exploiter=globals().get("_EXPLOITER"),
                    source_files=_rsf(target))
    findings = pipe.run(run_id, target, tid)
    if pipe.protocol_model is None:
        pipe.protocol_model = globals().get("_PRECOMPUTED_PROTOCOL")

    md = render_markdown({"target": tid, "run_id": run_id, "protocol": pipe.protocol_model}, findings)
    out = a.report or f"results/report-{run_id}.md"
    with open(out, "w") as fh:
        fh.write(md)
    # responsible-disclosure package (confirmed findings only)
    from .disclosure import build_disclosure, render_markdown
    dpkg = build_disclosure(findings, tid)
    with open(f"results/disclosure-{run_id}.md", "w") as fh:
        fh.write(render_markdown(dpkg))
    if a.kg:
        from .codeintel import extract as _ci
        from .kg import KnowledgeGraph
        g = KnowledgeGraph.from_model(_ci(target))
        g.attach_findings(findings)
        g.save(f"results/kg-{run_id}.db")
        print(f"[kg] {g.stats()} + unguarded_writers={len(g.unguarded_state_writers())}")
    rep = sum(1 for f in findings if f.reportable)
    proven = sum(1 for f in findings if f.tier.value == "PROVEN")
    print(f"[done] findings={len(findings)} reportable={rep} proven={proven}")
    print(f"[report] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
