# DECISIONS (ADR-style log)

Each: context · decision · rationale · reversibility.

## D1 — Fully local, no frontier API
User requirement: avoid per-run frontier API cost for an always-on research lab. Local model + tool-grounded verification. Reversible: an off-by-default API "escalation" hook may be added later.

## D2 — Hardware: g4dn.xlarge (T4 16GB), us-east-1
Chosen after g6e/L40S and g5/A10G hit "insufficient capacity" and us-west-2 had 0 GPU quota. T4 is reliably available and launches. Reversible: stop→change instance type→start (EBS persists) to move up to a 24-48GB GPU.

## D3 — Inference model: config-driven, default Qwen2.5-Coder (Apache-2.0, non-gated)
Fits T4 at 4-bit, strong on code, no HF token needed. Held in `config/model.yaml` (id+revision+quant) so swapping is one edit. Size (7B vs 14B) per user answer / benchmark.

## D4 — Repo location: authored on Mac (`~/seclab-web3`), run on EC2
Develop-local (good tooling + version control) / run-remote (GPU + fuzzing). Code synced to box; big weights live on box NVMe scratch, not in git.

## D5 — ECC: cherry-pick, don't install
Borrow authoring formats + `the-security-guide.md` hardening checklist + a few seed skills. Skip the 300+ irrelevant dev skills. See ECC-REVIEW.

## D6 — Training pipeline is first-class code, model-agnostic
Per user: switching base model to train must require only config edits. `config/train.yaml` + `config/datasets.yaml` manifest; license-gated loader. (Phase 7)

## D7 — Git: incremental atomic conventional commits, never push
User pushes manually. **No AI attribution in commit messages** — this is the user's private research work, consistent with their standing preference. Reversible on request.

## D8 — Training-data license policy: permissive-only by default
Apache/MIT/CC0 so any resulting model/adapter is safe to keep/share. Confirm via user answer; broaden only on explicit opt-in.

## D8 — UPDATE 2026-11-05
Training-data policy broadened per user: **any publicly available source** is allowed. The dataset loader records each source's license; the resulting model/adapter is **not redistributed** unless licenses later confirmed permissive. Default inference model stays Apache-2.0.

## D9 — Production-grade bar (no compromise)
User directive: no slacking, nothing half-built, no "v1" shortcuts — especially the orchestrator/harness. Every phase ships: real error handling, structured logging, idempotent + pinned provisioning, automated tests for its core logic, and a **runbook** in `docs/runbooks/` + a usage guide where a human operates it. "Works on a happy path" is not done.

## D10 — Authorization model
Confirmed: targets unrestricted except by the user's own authorization. Per-target `config/authorization.yaml` record (basis: own|bounty|engagement) is mandatory and checked by the scope gate (Phase 6, but the schema + gate stub land early). PoCs sandboxed to forks always.

## D11 — Inference model pinned: Qwen2.5-Coder-14B-Instruct @ Q4
Fits T4 16GB. Config-driven; swapping is one edit to `config/model.yaml`.

## D4 — UPDATE 2026-11-05: canonical home is EC2
Per user: the lab lives entirely on the box (repo, git, code, models, runs) — fully
self-contained "local lab on my EC2". Authored and run over SSH; Mac is only a terminal.

## D7 — UPDATE 2026-11-05: pushing enabled
User provided a dedicated passwordless deploy key at ~/.ssh/id_ed25519 and a git
remote, and asked the assistant to push after each commit. Repo core.sshCommand set
to that key. Commits remain clean (no AI attribution).
