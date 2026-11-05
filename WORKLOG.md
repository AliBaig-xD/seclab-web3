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

## 2026-11-05 · Phase 1 · toolchain resolved; two checker bugs fixed
- Resolved versions: slither 0.11.6, semgrep 1.183.0, halmos 0.3.3, echidna 2.4.0,
  medusa 1.5.1, mythril v0.24.8 (isolated image), solc 0.8.28, foundry forge 1.9.0.
- Fixes: aderyn asset picker grabbed the -update installer (now excludes update/installer
  and handles .tar.xz); doctor used a login shell that wiped foundry's PATH (now bash -c).
- Pushing enabled (D7 update).

## 2026-11-05 · Phase 1 · GATE PASSED (doctor ALL GREEN)
- Verified: forge/anvil/cast 1.9.0, slither 0.11.6, semgrep 1.183.0, halmos 0.3.3,
  echidna 2.4.0, medusa 1.5.1, aderyn 0.6.8, solc 0.8.28, mythril v0.24.8 (isolated),
  model qwen2.5-coder:14b deterministic probe OK.
- Froze versions in config/versions.env; captured docker/requirements.lock.txt; pinned model digest.
- Follow-up (Phase 1 hardening, tracked): rebuild Dockerfile from pinned tags + lock for byte-repro.
- Gate: PASS. Phase 1 DONE.

## 2026-11-05 · Phase 3/4 · dynamic engine PROVEN on real tooling
- Built self-contained reentrancy fixture (eval/corpus/reentrancy-etherstore, no forge-std dep).
- forge test in sandbox container: [PASS] test_exploit_drains_store — EtherStore drained to 0.
- Container pattern locked: root-in-container (the sandbox) + HOME=/cache on scratch for
  solc/svm caches; tools live under /root so --user is not used.
- Fixed git author identity to AliBaig-xD GitHub noreply (was dev@archrco.com).

## 2026-11-05 · Phase 3/4 · REAL end-to-end pipeline proven
- Wired SlitherScanner + FoundryPoCVerifier + correlation Pipeline + CLI (orchestrator/cli.py).
- Live run on reentrancy-etherstore: reentrancy -> PROVEN [HIGH] (slither + passing PoC + repro);
  solc-version/low-level-calls correctly demoted to CANDIDATE (not reported). 38 tests green.
- Orchestrator runs on host python3 (has pyyaml 6.0.3); tools via docker (host paths).
- Added scripts/hf_push.sh (private HF upload for trained adapters).
- NEXT: live-target ingestion (Sourcify/Etherscan source + anvil fork); broaden scanners
  (semgrep/aderyn), symbolic (halmos/mythril), fuzz (echidna/medusa); live LLM researcher;
  exploitation agent (LLM-generated PoC); then Phase 7 training pipeline.
