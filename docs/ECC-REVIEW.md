# ECC Repo Review — what we borrow

Source: https://github.com/affaan-m/ECC (general-purpose cross-assistant coding plugin). License: check `LICENSE` before copying any file verbatim.

## Verdict
Not a web3 security toolkit. Do **not** install wholesale. Cherry-pick:

| Item | Use for us | Action |
|------|-----------|--------|
| `the-security-guide.md` | Agentic-security hardening: our LLM ingests attacker-controlled contract source → prompt-injection surface. Sandboxing, approval boundaries, kill switches, observability. | Fold checklist into WORKFLOW Layer 2 + Phase 1 sandbox. |
| Authoring formats (agent md+frontmatter, skill sections, hook JSON) | Keep our own agents/skills portable & consistent. | Adopt as convention. |
| Agent archetypes: `planner`, `spec-miner`, `security-reviewer`, `silent-failure-hunter`, `code-explorer`, `loop-operator` | Mirror the roles in our orchestrator agents. | Reference, re-implement for EVM. |
| Seed skills: `defi-amm-security`, `evm-token-decimals`, `security-bounty-hunter` | Thin seed domain knowledge for the KB. | Read; extract facts into `knowledge/`. |
| Research playbook (evidence trail) | Seed only — our proof-gating is stricter. | Superseded by WORKFLOW. |

## Skip
300+ language/dev skills, build-resolvers, marketing/SEO/a11y agents, multi-assistant portability layers (.cursor/.codex/.gemini/.kiro/…), auto-generated guardrails.
