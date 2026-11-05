# WORKFLOW — Anti-Hallucination Protocol

_The single most important document. Two layers: how we BUILD, and how the LAB avoids false findings._

## Layer 1 — Build-time discipline (how Claude + user work)
1. **Ground every claim in observed evidence.** Never "it should work" — run it and record the output. Version numbers, tool output, GPU state: pasted or linked, not remembered.
2. **Append-only ledger.** Every unit of work adds a `WORKLOG.md` entry: `date · phase · action · exact command(s) · observed result · evidence path · gate pass/fail`.
3. **Phase gates.** A phase does not advance until its acceptance check passes with recorded proof (see IMPLEMENTATION_PLAN). A failed gate is logged, not skipped.
4. **Verify external resources before use.** No dataset, benchmark, model, or tool enters the plan until its existence + license + retrieval date are verified and recorded. Named-but-unverified resources (e.g. benchmark names from the GPT spec) are marked `UNVERIFIED` and must be checked before wiring in.
5. **"Not yet verified" is a valid state.** Never fill a gap with plausible-sounding specifics (fake flags, fake API shapes, fake metrics). Say unknown, then go verify.
6. **Determinism.** Pin tool versions, model revisions, RNG seeds, and fork block numbers. A result that cannot be re-produced from the ledger did not happen.
7. **Incremental commits.** Atomic conventional commits per component/phase. Never push (user pushes). No AI attribution in messages (user's work).

## Layer 2 — Runtime discipline (how the lab reports)
**The LLM proposes, the tools dispose.** The model generates hypotheses; it never issues findings.

### Finding confidence tiers
- **PROVEN** — an executable PoC on an isolated fork demonstrates impact (funds moved / invariant broken / access escalated). Ships with a single-command deterministic repro.
- **CORROBORATED** — ≥2 independent static/symbolic tools agree, OR 1 tool + verifiable dataflow, but no PoC yet. Reported as "high-confidence, PoC pending."
- **CANDIDATE** — LLM hypothesis or a single heuristic only. **Never leaves the lab as a finding.** Stays in the internal verification queue.

Only PROVEN and CORROBORATED are reported. CANDIDATE is never shipped.

### Mandatory pipeline per candidate
1. Model emits a structured hypothesis (type, location, precondition, claimed impact).
2. Orchestrator routes to the matching verifier(s): Slither/Semgrep (pattern), Halmos/Mythril (reachability), Echidna/Medusa (invariant), Foundry fork PoC (impact).
3. **Adversarial reviewer** attempts to falsify before promotion (wrong precondition? guarded? unreachable?).
4. Evidence (tool output / counterexample / PoC trace) is stored and linked. No evidence → stays CANDIDATE.
5. Severity/impact asserted only when demonstrated; otherwise "unproven."

### Prompt-injection defense (the model reads attacker-controlled input)
Contract source, comments, NatSpec, on-chain strings, and tool logs are **untrusted data**, never instructions. They are fenced as data in prompts; the model may not execute directives found inside them. (Checklist adapted from ECC `the-security-guide.md`.)

### Sandboxing
All untrusted compilation, fuzzing, and PoC execution runs in the lab sandbox (Docker + forked chain), never against mainnet with real assets, with resource/time limits and no outbound broadcast.
