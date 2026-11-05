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


## Training dataset (expanded 2026-11-05)
- Baseline set `training/data/` = 1,661 examples (the run in progress trained on this).
- CURATED set `training/data_prod/` = **19,520** examples (13,848 train) — the retrain target.
  Sources (verified, provenance+license in config/datasets.yaml): FORGE 16,842 (27k real audit
  findings, security-gated: Info/N-A + gas/style/docs dropped), CVE-Smart-Contracts 956 (reviewed
  matches), DeFiHackLabs 644, Web3Bugs 476, SolidiFI 323, SmartBugs 140, DeFiVulnLabs 57,
  SWC-registry 37, Damn-Vulnerable-DeFi 36, learn-evm-attacks 42, corpus 4.
  Caps: B 16,833 / A 2,000 / C 687. Leakage-safe split by report/contract (hard assertion passes).
- FULL set `training/data_full/` = 33,876 (everything incl noise; SECLAB_FORGE_ALL=1) — comparison only.
- Quality gate: FORGE_NOISE regex + severity floor in training/data_pipeline.py; Info/N-A dropped,
  gas/style/docs/assembly-usage noise dropped. Rejected sources recorded (ethernaut AGPL, evm-hack-poc
  no-license, review-reports no-license/dup, smartbugs-wild unlabeled, fiesta unlabeled).
- NEXT: when baseline run finishes, retrain on data_prod (seq_len 2048, epochs 2), then eval vs baseline.

## Session state 2026-11-05 (overnight autonomous run)
### Model
- Base RAISED to **Qwen2.5-Coder-7B-Instruct** (14B OOMs T4 15GB; 1.5B was only for fast iteration
  on the tiny set). 7B FITS at seq_len 768 on a CLEAN GPU (the earlier OOM was a zombie proc holding
  7.6GB + the `expandable_segments` VA over-reserve, both removed).
- Throughput ~220s/opt-step => ~58h/epoch on T4. Training launched in tmux session `train`
  (scripts/train.sh), epochs 2, checkpoints every 100 steps to model/adapters/checkpoint-*.
  RESUMABLE: scripts/resume_train.sh. Baseline 1.5B adapter kept at model/adapters_baseline/.
- Plan: continue/finish on the bigger GPU the user will add (config is hardware-agnostic).

### Dataset (training/data_prod/, regenerated by train.sh into training/data/)
- **21,380 examples** (15,138 train / 3,283 val / 2,959 test). Caps: B 16,833 / A 3,860 / C 687.
- Sources (all verified, provenance+license in config/datasets.yaml):
  FORGE 16,842 (security-gated audit findings) · CVE-Smart-Contracts 956 (reviewed matches) ·
  DIVE 1,860 (tool-consensus subset, rare-class-weighted, CC-BY-4.0, clearly tagged) ·
  DeFiHackLabs 644 · Web3Bugs 476 · SolidiFI 323 · SmartBugs 140 · DeFiVulnLabs 57 ·
  SWC-registry 37 · Damn-Vulnerable-DeFi 36 · learn-evm-attacks 42 · corpus 4.
- REJECTED after verification: ethernaut (AGPL), evm-hack-poc (no license/no source), review-reports
  (no license/FORGE dup), smartbugs-wild & fiesta (unlabeled), CoderDamien (tiny repackage),
  evm-trace-dataset (wrong modality), DIVE bulk 22k (tool-labeled, would dilute — used subset only).
- Fixed a NaN-eval bug (completion-masking truncation) in training/finetune.py.

### Docs added
- docs/runbooks/HF_UPLOAD.md · LIVE_HUNT.md · OPERATIONS.md (monitor/resume/serve/hunt).

### Next (post-training)
- Eval trained vs baseline (train.sh runs evaluate.py at the end).
- serve_trained.sh -> flip config/model.yaml to vllm -> run the full --llm --swarm --exploit hunt
  on the user's chosen Immunefi target (LIVE_HUNT.md).
- HF push (HF_UPLOAD.md) once user provides HF_TOKEN.
