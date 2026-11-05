# RESUME — READ FIRST after any restart or context compaction

This is the living "where are we RIGHT NOW" anchor. `WORKLOG.md` is append-only
history; THIS file is the current snapshot. Update it at every phase boundary.

## What this is
seclab-web3: a fully-local, production-grade EVM security-research lab. A local LLM
proposes hypotheses; proven tools verify; **nothing is a "finding" without machine
evidence or an executable PoC**. Full scope in `SCOPE.md`; the law is `docs/WORKFLOW.md`.

## Canonical home = EC2 (the Mac is only a terminal)
- Box: `ubuntu@52.23.218.124` — g4dn.xlarge, Tesla **T4 16GB**, us-east-1
- Connect: `ssh -i ~/Downloads/tess-quiet-aws.pem ubuntu@52.23.218.124`
- Repo on box: `/home/ubuntu/seclab-web3`
- Git remote: `origin git@github.com:AliBaig-xD/seclab-web3.git`, branch `main`
  (push key: `/home/ubuntu/.ssh/id_ed25519`; repo `core.sshCommand` already set)
- Scratch (models/forks/runs — NOT in git): `/opt/dlami/nvme/seclab`
- Model server: ollama container `seclab-ollama` @ `127.0.0.1:11434`, model `qwen2.5-coder:14b`

## Operating rules (do not drift)
- Build AND run on the box over SSH. Author files there (heredocs / staged scripts).
- Unit tests run in a clean python:3.11 container: `bash scripts/test.sh`.
- Commit atomically (conventional messages, **no AI attribution**) AND **push after each commit**.
- Anti-hallucination law (`docs/WORKFLOW.md`): the model emits ONLY hypotheses; a
  Finding's tier is DERIVED from evidence — PROVEN = PoC + repro, CORROBORATED = >=2
  independent tools, else CANDIDATE (never reported). Contract source = untrusted,
  injection-fenced. PoCs run only on sandboxed Anvil forks.

## Re-orient in 30 seconds
    ssh -i ~/Downloads/tess-quiet-aws.pem ubuntu@52.23.218.124
    cd ~/seclab-web3
    git log --oneline | head -20     # what's done
    tail -40 WORKLOG.md              # latest ledger entries
    cat RESUME.md                    # this file: status + next step
    bash scripts/test.sh             # unit tests must be green
    bash scripts/doctor.sh           # env/tool gate

## STATUS — as of 2026-11-05 (UPDATE THIS at each phase boundary)
Complete production-grade EVM security lab + specialized-model training. All on EC2, pushed.
107 unit tests green; 0 stubs/TODOs; container-hardened; CI wired.

CORE (built + validated end-to-end):
- Agentic harness (`seclab` CLI): per-run artifact dirs, logs, manifest, run index. Phases
  3/4/5 all built. Proof gate: PROVEN=dynamic proof+repro, CORROBORATED=2 tools, else CANDIDATE.
- Engines: slither/aderyn/semgrep + mythril(multi-file)/halmos + echidna/medusa + foundry PoC
  + differential. Swarm map-reduce, code intel+KG, protocol intel, LLM hunter(RAG), reviewer,
  exploitation agent. On-chain ingest (Sourcify + Etherscan fallback). Disclosure, triage.
- Full agentic run validated: LLM+swarm+RAG+reviewer+protocol+PoC -> PROVEN in ~36s.

IMPROVEMENT LEVERS (built on top): invariant->harness synthesis, self-improvement flywheel,
multi-sample hypotheses, reviewer voting (--thorough), Halmos->PoC, Etherscan fallback,
parallel scanners (--parallel). docs/LIMITATIONS.md lists all 14 limitations honestly.

TRAINING: production QLoRA pipeline + ~1661-example curated multi-source dataset (644 real
DeFiHackLabs PoCs) + self-improvement flywheel. Real metrics (ppl + detection acc + PoC
structural). RUNNING NOW: Qwen2.5-Coder-1.5B, 2 epochs (~2.5h) -> real adapter.

PENDING (post-training, needs GPU/CPU free): full lab benchmark (all engines); live-ground
the new levers (invariant synth, Halmos->PoC, mythril multi-file, differential); report
trained-adapter metrics; serve the trained model (vLLM base+adapter, or merge->GGUF for
ollama). Remaining big levers: Go/Rust client analyzer, web dashboard, Dockerfile digest pin.

## Map
`SCOPE.md` · `docs/WORKFLOW.md` (law) · `docs/IMPLEMENTATION_PLAN.md` (phases+gates) ·
`docs/DECISIONS.md` (why) · `WORKLOG.md` (history) · `orchestrator/` (harness) ·
`tests/` · `docker/` (toolchain) · `scripts/` (provision/doctor/test/sync).
