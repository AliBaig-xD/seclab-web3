# WORKLOG (append-only)

Format: `date · phase · action · command/evidence · result · gate`

---

## 2026-11-05 · Phase 0 · EC2 box verified (ground truth)
- Command: `ssh ubuntu@52.23.218.124 'nvidia-smi; nproc; free -h; df -h /; lsblk'`
- Result: **g4dn.xlarge**, Tesla **T4 16GB VRAM**, driver 595.112 / CUDA 13.2, 4 vCPU, 15GB RAM, 193GB root free, 116GB NVMe scratch at `/opt/dlami/nvme`.
- Toolchain present: git, python3 (**3.14.4 — too new for ML wheels; use DLAMI env**), pip3, docker, jq, curl. **Missing: node, npm, cargo** (install Phase 1).
- Implication recorded: 16GB VRAM → local model ceiling ≈ 7B-14B quantized. 32B deferred to a future bigger GPU (EBS persists; resize is non-destructive).
- Gate: PASS (reality captured before any build).

## 2026-11-05 · Phase 0 · ECC repo surveyed
- Command: `git clone --depth 1 https://github.com/affaan-m/ECC`; inventoried agents/skills/hooks.
- Result: general-purpose cross-assistant coding plugin (71 agents, 314 skills, mostly language build-resolvers). Not a web3 toolkit. Decision + borrow list in `docs/ECC-REVIEW.md`.
- Gate: PASS.

## 2026-11-05 · Phase 0 · Governance scaffold authored
- Wrote: README, SCOPE, WORKFLOW (anti-hallucination), IMPLEMENTATION_PLAN, DECISIONS, ECC-REVIEW, repo skeleton, .gitignore. `git init` done.
- Gate: pending initial commit.

## 2026-11-05 · Phase 0 · Decisions locked from user answers
- Auth scope: any target within user authorization → per-target auth record + scope gate; PoCs sandboxed. (SCOPE updated, D10.)
- Inference model: Qwen2.5-Coder-14B-Instruct Q4 (D11).
- Training data: any public, license recorded, model not redistributed (D8 update).
- Standard: production-grade, runbooks + guides mandatory (D9).
- Gate: PASS.
