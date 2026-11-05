"""The research harness: a production agentic orchestrator that drives an end-to-end
security investigation and coordinates the agent roles (ingest -> code intelligence ->
authorization -> hypothesis (static + LLM + swarm + protocol) -> verification ->
exploitation -> adversarial review -> triage -> report -> disclosure). Every run gets a
run directory with all artifacts, structured logs, and a manifest."""
from __future__ import annotations
import json, logging, os, time
from dataclasses import dataclass
from .config import load_model_config
from .model_client import make_client
from .authorization import ScopeGate
from .evidence import EvidenceStore
from .pipeline import Pipeline
from .report import render_markdown
from .disclosure import build_disclosure, render_markdown as render_disclosure
from .ingest import read_source_files, read_sources
from .schema import finding_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class ScanOptions:
    llm: bool = False
    swarm: bool = False
    rag: bool = False
    exploit: bool = False
    differential: bool = False
    fast: bool = False
    poc_test: str = None
    poc_family: str = "reentrancy"
    swarm_concurrency: int = 1
    verbose: bool = False


def _logger(run_dir, verbose):
    lg = logging.getLogger(f"seclab.{os.path.basename(run_dir)}")
    lg.handlers = []
    lg.setLevel(logging.DEBUG if verbose else logging.INFO)
    fh = logging.FileHandler(os.path.join(run_dir, "run.log"))
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    lg.addHandler(fh)
    lg.addHandler(ch)
    lg.propagate = False
    return lg


class ResearchHarness:
    def __init__(self, model_config=None):
        self.mc = model_config or load_model_config()

    def _scanners(self, opt: ScanOptions):
        from .tools.slither import SlitherScanner
        from .tools.aderyn import AderynScanner
        from .tools.semgrep import SemgrepScanner
        s = [SlitherScanner(), AderynScanner(), SemgrepScanner()]
        if opt.differential:
            from .tools.differential import DifferentialScanner
            s.append(DifferentialScanner())
        if not opt.fast:
            from .tools.mythril import MythrilScanner
            from .tools.halmos import HalmosScanner
            from .tools.echidna import EchidnaScanner
            from .tools.medusa import MedusaScanner
            s += [MythrilScanner(), HalmosScanner(), EchidnaScanner(), MedusaScanner()]
        return s

    def _llm_stack(self, target, opt, log):
        """Returns (researcher, reviewer, protocol, seed_hypotheses, exploiter, protocol_model_holder)."""
        if not (opt.llm or opt.swarm):
            return None, None, None, [], None
        client = make_client(self.mc)
        if not client.available():
            log.warning("model endpoint unavailable; proceeding with tools only")
            return None, None, None, [], None
        from .researcher import Researcher
        from .reviewer import LLMReviewer
        from .protocol import ProtocolIntelligence
        kb = None
        if opt.rag:
            from .knowledge import KnowledgeBase
            kb = KnowledgeBase(os.path.join(ROOT, "knowledge", "kb.db"))
            if kb.count() == 0:
                kb.seed_from_cards(os.path.join(ROOT, "knowledge", "cards.json"))
            log.info(f"RAG knowledge base: {kb.count()} cards")
        researcher = Researcher(client, kb=kb)
        reviewer = LLMReviewer(client)
        protocol = ProtocolIntelligence(client)
        exploiter = None
        if opt.exploit:
            from .exploit import ExploitationAgent
            exploiter = ExploitationAgent(client)
        seed = []
        if opt.swarm:
            from .codeintel import extract as ci_extract, build_slices, interaction_pairs
            from .swarm import SwarmEngine
            from .ingest import source_for_contract
            ci = ci_extract(target)
            slices, pairs = build_slices(ci), interaction_pairs(ci)
            files = read_source_files(target)
            srcs = {c["contract"]: source_for_contract(files, c["contract"]) for c in ci.get("contracts", [])}
            pm = protocol.analyze(read_sources(target))
            eng = SwarmEngine(client, concurrency=opt.swarm_concurrency, kb=kb)
            seed = eng.run(slices, pairs, srcs, pm)
            log.info(f"swarm: slices={eng.stats['slices']} deep={eng.stats['deep']} "
                     f"pairs={eng.stats['pairs']} hypotheses={len(seed)}")
            researcher = None  # swarm supersedes single-shot
        return researcher, reviewer, protocol, seed, exploiter

    def run(self, *, local=None, onchain=None, chain=1, basis=None, target_id=None,
            opt: ScanOptions = None, run_id=None) -> dict:
        opt = opt or ScanOptions()
        run_id = run_id or f"run-{int(time.time())}"
        run_dir = os.path.join(ROOT, "results", "runs", run_id)
        os.makedirs(run_dir, exist_ok=True)
        log = _logger(run_dir, opt.verbose)
        t_start = time.time()
        phases = {}

        def phase(name):
            phases[name] = time.time()
            log.info(f"=> {name}")

        # --- ingest + authorize ---
        phase("ingest")
        if onchain:
            from .onchain import ingest_onchain
            scratch = os.environ.get("SECLAB_SCRATCH", "/opt/dlami/nvme/seclab")
            target = f"{scratch}/onchain-{onchain.lower()}"
            import subprocess
            subprocess.run(["sudo", "rm", "-rf", target])
            info = ingest_onchain(onchain, chain, target)
            if not info:
                log.error(f"no verified source for {onchain} on chain {chain}")
                return {"error": "no-verified-source", "run_dir": run_dir}
            tid = target_id or onchain.lower()
            log.info(f"ingested {onchain}: solc={info['solc']} files={info['nfiles']} main={info['main']}")
            if not basis:
                log.error("on-chain target requires an authorization basis")
                return {"error": "no-authorization-basis", "run_dir": run_dir}
            gate = ScopeGate.ephemeral(tid, basis, poc_allowed=bool(opt.poc_test), affirmed_by="dev@archrco.com")
        else:
            target = os.path.abspath(local)
            tid = target_id or os.path.basename(target.rstrip("/"))
            gate = ScopeGate(os.path.join(ROOT, "config", "authorization.yaml"))
        rec = gate.assert_authorized(tid, poc=bool(opt.poc_test))
        log.info(f"authorized: {tid} basis={rec.get('basis')} poc={bool(opt.poc_test)}")

        # --- code intelligence + KG ---
        phase("code-intelligence")
        from .codeintel import extract as ci_extract
        from .kg import KnowledgeGraph
        ci = ci_extract(target)
        kg = KnowledgeGraph.from_model(ci)
        log.info(f"code intelligence: {kg.stats()} unguarded_writers={len(kg.unguarded_state_writers())}")

        # --- hypothesis + verification ---
        phase("hypothesis+verification")
        researcher, reviewer, protocol, seed, exploiter = self._llm_stack(target, opt, log)
        scanners = self._scanners(opt)
        verifiers = []
        if opt.poc_test:
            from .tools.foundry import FoundryPoCVerifier
            verifiers.append(FoundryPoCVerifier(opt.poc_test, opt.poc_family))
        llm_code = read_sources(target) if (researcher is not None) else None
        store = EvidenceStore(os.path.join(run_dir, "evidence.db"))
        pipe = Pipeline(store, scanners, verifiers, reviewer=reviewer, researcher=researcher,
                        llm_code=llm_code, protocol=protocol, seed_hypotheses=seed,
                        exploiter=exploiter, source_files=read_source_files(target))
        findings = pipe.run(run_id, target, tid)

        # --- outputs ---
        phase("report")
        kg.attach_findings(findings)
        kg.save(os.path.join(run_dir, "kg.db"))
        md = render_markdown({"target": tid, "run_id": run_id, "protocol": pipe.protocol_model}, findings)
        open(os.path.join(run_dir, "report.md"), "w").write(md)
        open(os.path.join(run_dir, "disclosure.md"), "w").write(
            render_disclosure(build_disclosure(findings, tid)))
        with open(os.path.join(run_dir, "findings.json"), "w") as f:
            json.dump([finding_json(x) for x in findings], f, indent=2)

        reportable = [f for f in findings if f.reportable]
        proven = [f for f in findings if f.tier.value == "PROVEN"]
        from .tools.base import tool_versions
        import sqlite3
        idx = sqlite3.connect(os.path.join(ROOT, "results", "run_index.db"))
        idx.execute("CREATE TABLE IF NOT EXISTS runs(run_id TEXT, target TEXT, basis TEXT, "
                    "findings INT, reportable INT, proven INT, wall_s REAL, ts TEXT)")
        idx.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,datetime('now'))",
                    (run_id, tid, rec.get("basis"), len(findings), len(reportable),
                     len(proven), round(time.time() - t_start, 1)))
        idx.commit(); idx.close()
        manifest = {
            "tool_versions": tool_versions(),
            "run_id": run_id, "target": tid, "basis": rec.get("basis"),
            "options": opt.__dict__, "engines": "fast" if opt.fast else "full",
            "findings": len(findings), "reportable": len(reportable), "proven": len(proven),
            "code_intel": kg.stats(),
            "phase_timings_s": {k: round((phases.get(nxt, time.time()) - v), 1)
                                for (k, v), nxt in zip(phases.items(), list(phases)[1:] + [None])},
            "wall_s": round(time.time() - t_start, 1),
            "artifacts": sorted(os.listdir(run_dir)),
        }
        with open(os.path.join(run_dir, "run_manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)
        log.info(f"DONE: findings={len(findings)} reportable={len(reportable)} "
                 f"proven={len(proven)} wall={manifest['wall_s']}s")
        log.info(f"artifacts -> {run_dir}")
        return {"run_id": run_id, "run_dir": run_dir, "findings": findings,
                "reportable": len(reportable), "proven": len(proven), "manifest": manifest}
