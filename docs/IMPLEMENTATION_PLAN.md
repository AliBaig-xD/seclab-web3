# IMPLEMENTATION PLAN

Full EVM breadth, built in gated phases. Nothing is descoped — phases order the work so each one is independently useful and provable. No phase advances until its **Gate** passes with proof in `WORKLOG.md`. Each phase ends with atomic commits (no push).

## Phase 0 — Foundation & governance  ← current
Repo, SCOPE, WORKFLOW, this plan, DECISIONS, ECC review, WORKLOG seeded with verified box facts.
**Gate:** docs exist and reflect verified reality; initial commit made.

## Phase 1 — Reproducible box environment
Install on EC2, pinned + Dockerized: Foundry (forge/anvil/cast), Slither, Aderyn, Semgrep, Echidna, Medusa, Mythril, Halmos, Node, Rust, Python ML env (use DLAMI's, not system 3.14). `scripts/doctor.sh` verifies every tool + GPU and records versions.
**Gate:** `doctor.sh` green; all versions in WORKLOG.

## Phase 2 — Local model serving (config-driven, swappable)
Pull the configured base model (default Qwen2.5-Coder, Apache-2.0, non-gated → no token) in a quant that fits the T4; serve via Ollama/llama.cpp. `config/model.yaml` holds model id + revision + quant so swapping is one edit. Benchmark tok/s + usable context.
**Gate:** deterministic answer to a fixed Solidity prompt; latency recorded.

## Phase 3 — Ingestion + static layer
Clone/compile targets (Foundry/Hardhat), build AST/call-graph/storage-layout (Slither), run Semgrep rules. Orchestrator skeleton + evidence store (SQLite). 
**Gate:** on a known-vulnerable contract, static hits recorded with evidence paths.

## Phase 4 — Verification engine (the "tools dispose" core)
Foundry fork + PoC runner; Echidna/Medusa invariant fuzzing; Halmos/Mythril symbolic. Produces machine-checkable evidence objects.
**Gate:** a known reentrancy reproduced end-to-end by a passing Foundry PoC on a fork.

## Phase 5 — LLM researcher + RAG + adversarial reviewer
Knowledge base (EIPs/SWC/curated writeups — sources verified + licensed) in a vector store; hypothesis→verify loop; adversarial falsification pass; confidence-tier promotion.
**Gate:** on a holdout known bug, system runs hypothesis→verify→PROVEN finding with repro.

## Phase 6 — Reporting, triage, disclosure, authorization gate
Finding schema + tiers; triage (value/effort/risk, capped top-N + not-recommending list); report generator; responsible-disclosure workflow; machine-checkable authorization/scope gate (no analysis without an authorization record).
**Gate:** full report for a sample audit — only proof-gated findings, with repros.

## Phase 7 — Training pipeline (in code, model-agnostic)  [explicit user requirement]
`training/` QLoRA/LoRA pipeline, fully **config-driven** so switching the base model to train is one config edit:
- `config/train.yaml` — base model id/revision, quant, LoRA rank/alpha/lr/epochs, seq len.
- `config/datasets.yaml` — manifest of `{name, url, license, split}`; loader **rejects** non-permissive licenses by policy; every source UNVERIFIED until checked.
- Reproducible: pinned requirements, fixed seed, saved logs + eval report artifacts.
- Adapter output + model card written to `model/adapters/`.
**Gate:** a dry-run fine-tune on a tiny verified set completes and emits an eval report; swapping the base model id in config runs without code changes.

## Phase 8 — Evaluation harness + regression CI
Curated known/unseen corpus (every source verified + licensed; GPT-spec benchmark names confirmed or dropped). Metrics: recall, FP rate, PoC-repro rate, time-to-report. Regression suite re-runs on change.
**Gate:** baseline metrics recorded; negative-control set yields ~0 critical FPs.

## Operating mode during autonomous build
Work proceeds phase by phase without pausing for approval. Long box tasks run under tmux/background. Blockers or decisions that need the user are surfaced immediately; otherwise defaults in DECISIONS apply.

## Architecture components -> phases (full-spectrum, nothing descoped)
- Research orchestrator: Phase 3 (built: ingest+pipeline+CLI).
- Code intelligence (Tree-sitter/AST/call-graph/storage/dataflow): Phase 3b (planned).
- **Protocol intelligence** (economic assumptions, invariants, trust boundaries,
  protocol-level adversarial questions): Phase 5a (planned) — feeds the hunter + fuzz invariants.
- Vulnerability hunter (LLM researcher): Phase 5 (built: live 14B).
- Independent reviewer (adversarial falsification): Phase 5b (hook built; live reviewer planned).
- Validation lab: Phase 4 — Foundry/Anvil PoC built; Slither built; semgrep/aderyn/halmos/
  mythril/echidna/medusa adapters in progress.
- Live-target ingestion (Sourcify/Etherscan source + anvil --fork-url): Phase 3c (planned).
- Reporting + triage + disclosure: Phase 6 (built: proof-gated report + triage).
- RAG/KG (vector store): Phase 5c (planned).
- Exploitation agent (LLM-generated Foundry PoC, auto-iterated): Phase 4b (planned).
- Training (3-part, config-driven QLoRA on /opt/pytorch) + HF push: Phase 7 (planned; hf_push built).
- Evaluation harness + negative controls + regression CI: Phase 8 (planned).
