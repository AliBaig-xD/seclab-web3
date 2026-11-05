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
- Phase 0 (governance): DONE.
- Phase 1 (reproducible env): **DONE — doctor ALL GREEN.** Model server (14B, deterministic)
  + full analysis toolchain verified. Versions frozen in config/versions.env +
  docker/requirements.lock.txt. Re-verify anytime: `bash scripts/doctor.sh`.
- Harness code DONE + unit-tested (34 tests, `bash scripts/test.sh`): schema, evidence
  store, authorization scope gate, config, model_client, runner, slither parser,
  researcher (injection-fenced), triage, report. NOT yet wired to real tools.
- NEXT (Phase 3/4): wire the REAL verifiers (slither/semgrep/halmos/echidna/medusa +
  Foundry fork-PoC) into the runner and prove the full chain end-to-end on a known
  reentrancy contract (-> PoC drain on an Anvil fork). This is the key milestone.
- TRACKED follow-up (Phase 1 hardening): rebuild Dockerfile from pinned tags + lock
  for byte-level reproducibility.

## Map
`SCOPE.md` · `docs/WORKFLOW.md` (law) · `docs/IMPLEMENTATION_PLAN.md` (phases+gates) ·
`docs/DECISIONS.md` (why) · `WORKLOG.md` (history) · `orchestrator/` (harness) ·
`tests/` · `docker/` (toolchain) · `scripts/` (provision/doctor/test/sync).
