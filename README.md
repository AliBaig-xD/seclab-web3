# seclab-web3

Local, self-hosted EVM security-research lab. Standalone sibling of `~/seclab`.
Runtime lives on an EC2 GPU box; this repo is authored on the Mac and synced to the box.

**Read these first:**
- `SCOPE.md` — what this is, what it is not, authorization, success criteria.
- `docs/WORKFLOW.md` — the anti-hallucination protocol (how we build + how the lab avoids false findings). **Non-negotiable.**
- `docs/IMPLEMENTATION_PLAN.md` — phased build, each phase gated by recorded proof.
- `docs/DECISIONS.md` — decision log (ADR-style).
- `docs/ECC-REVIEW.md` — what we borrow from the ECC repo and why.
- `WORKLOG.md` — append-only ledger of what was actually done + evidence.

**Core rule:** the LLM proposes, the tools dispose. Nothing is a "finding" until a
deterministic tool or an executable PoC confirms it. See `docs/WORKFLOW.md`.
