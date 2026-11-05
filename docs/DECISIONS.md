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
