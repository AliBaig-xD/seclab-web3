# SCOPE

_Last updated: 2026-11-05_

## Purpose
A local, fully self-hosted lab that audits EVM systems by orchestrating proven
security tools with a local LLM acting as a hypothesis generator and triager.
Optimized for cost (no frontier API, no rented frontier GPU) and for **not emitting
false findings**.

## Honest capability statement
A local 7B-14B model on a single T4 will **not** match a senior auditor at
discovering novel logic bugs. That ceiling is accepted. The lab's value comes from:
(1) reliable coverage of known vulnerability classes, (2) tool-grounded verification,
(3) automatic PoC reproduction on forked chains. The model is the cheap part; the
tools and the proof-gating are the product.

## In scope (full EVM breadth — built in phases, nothing descoped)
- Languages: Solidity, Vyper, Yul/inline-assembly; compiler/optimizer behavior.
- Vuln classes: reentrancy, access control, delegatecall, arithmetic, init/upgrade,
  proxy patterns (EIP-1967/2535/minimal), ERC-20/721/1155 misuse, oracle/price,
  flash-loan/economic, cross-contract, governance.
- DeFi primitives: AMMs, lending, liquidations, vaults, bridges.
- EVM core: opcodes, gas, precompiles, storage/memory rules, tx semantics.
- Infra-adjacent: mempool/MEV scenarios, RPC surfaces (analysis, not live attack).
- Crypto flows: ECDSA, EIP-712, Merkle, ZK-verification call paths.
- Methods: static, fuzzing, symbolic, differential, fork-replay PoC.

## Out of scope
- Non-EVM chains.
- Any target that is not the user's own code, a public/authorized bug-bounty scope,
  or code under a signed engagement.
- Live mainnet transactions with real assets. PoCs run only on isolated forks.
- Producing exploit tooling for unauthorized use.

## Authorization (CONFIRMED 2026-11-05)
The lab may be pointed at any EVM target, but only within what the user is
authorized to test. Enforcement: a machine-checkable **authorization record** is
required per target before any run (`config/authorization.yaml`), asserting the
basis — `own` / `bounty:<program>` / `engagement:<id>` — and the user affirms it.
Static/read-only analysis is permitted broadly; **PoC execution is always sandboxed
to a local fork and never broadcast**. No target is processed without an auth record.

## Success criteria (v-complete)
- Ingest a mid-size EVM repo and produce a structured report where **every reported
  finding carries machine-checkable evidence or a passing PoC** (see WORKFLOW tiers).
- False-positive rate on a negative-control (clean) contract set ≈ 0 critical.
- Each finding reproduces via a single deterministic command.
- Runs entirely on the local box with the GPU off the public internet for inference.

## Non-negotiables
- Sandbox-only execution of untrusted code and PoCs.
- Proof-gated findings (no LLM-only claims leave the lab as "findings").
- Append-only `WORKLOG.md`; decisions recorded in `docs/DECISIONS.md`.
- No external resource (dataset/benchmark/model) enters the plan until its existence
  and license are verified and recorded.

## Full-spectrum scope confirmation (2026-11-05)
Everything below is IN SCOPE. Build order lives in docs/IMPLEMENTATION_PLAN.md;
"planned, not yet built" never means out of scope.

### EVM research domains (each with its own vuln taxonomy)
EVM execution (opcodes/gas/memory/storage/call semantics/precompiles) · Solidity
(compiler/optimizer/ABI/Yul/inheritance/storage layout) · Vyper (compiler/semantics) ·
all smart-contract vuln classes + variants · DeFi (lending/AMM/derivatives/vaults/
staking/liquidation) · Cryptography (ECDSA/hashing/signatures/Merkle/ZK) · Proxies
(UUPS/transparent/beacon/diamond/custom) · Bridges (message verification/replay/finality/
cross-domain) · MEV (ordering/sandwich/censorship) · Governance (voting/delegation/
timelocks) · L2 (optimistic/ZK rollups, sequencers, proofs, withdrawals) · Clients
(Geth/Reth/Nethermind/Besu) · Consensus / EL-CL interaction / finality · RPC + infra ·
Compiler security (optimizer miscompilation, differential testing) · Economic security
(game theory/incentives/accounting) · Formal verification (SMT/symbolic/invariants/model
checking) · Historical research (CVEs/audits/incident postmortems).

### Architecture components (the senior-researcher workflow)
1. Research orchestrator — repo, scope, dependencies, protocol architecture.
2. Code intelligence — AST, call graphs, inheritance, data flow, storage layout (Tree-sitter + solc AST).
3. **Protocol intelligence (the crux)** — economic assumptions, invariants, trust
   boundaries, roles; asks protocol-level adversarial questions (stale oracle? price
   manipulation between state transitions? rounding bypass of liquidation? flash-liquidity
   solvency? exploitable interaction between two individually-correct functions? unexpected
   privileged config/impl change?). First-class component, not an afterthought.
4. Vulnerability hunter — hypothesis generation + attack-path analysis (LLM).
5. Independent reviewer — challenges findings, eliminates false positives.
6. Validation lab — Foundry/Anvil + Echidna/Medusa + Halmos/Mythril + differential testing.
7. Reporting — reproducible PoC, impact analysis, severity, remediation, audit report.

### Tech stack (substitutions noted)
Foundry/Solidity · Slither + Aderyn (static) · Echidna + Medusa (fuzz) · Halmos + Mythril
(symbolic) · Anvil (local exec/fork) · Tree-sitter + solc AST + custom call-graph (code
intel) · model serving: Ollama (llama.cpp engine; vLLM swappable via config/model.yaml) ·
retrieval: self-hosted vector store (pgvector/Qdrant-class) · Python orchestration ·
results: SQLite now (Postgres-compatible schema) + structured JSON + Markdown reports.

### Training strategy (Phase 7) — THREE capabilities, not one blob
A. Solidity security reasoning — reentrancy variants, access control, delegatecall/proxy,
   signature/replay, oracle manipulation, arithmetic/precision, cross-contract.
B. DeFi protocol reasoning — lending/borrowing, AMM/DEX, liquidation, vaults/yield,
   bridges, staking/restaking, governance, flash-loan interactions.
C. Security research methodology — form testable hypotheses, trace execution paths,
   distinguish suspicious from exploitable, generate reproducible Foundry PoCs, explain
   preconditions + impact, verify proposed fixes.
Datasets (verify license/provenance/labels + NO train-eval leakage of vuln/patched pairs):
SmartBugs (+ consolidated ground truth), CVE Smart Contracts (Aug 2026, 491 labeled),
SolidiFI (injected vulns), Web3Bugs (real-world findings).

### Success criterion (north star)
Independently investigate an UNFAMILIAR EVM system -> identify a genuine weakness ->
construct a safe reproducible demonstration (fork PoC) -> explain root cause -> withstand
adversarial review. Not agent count, not CVE memorization, not impressive-sounding prose.
