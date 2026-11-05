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

## Authorization (CONFIRM — currently an assumption)
ASSUMPTION until the user confirms: targets are limited to (a) the user's own
contracts, (b) public bug-bounty programs whose scope explicitly permits this, and
(c) engagements with written authorization. A machine-checkable scope gate is built
in Phase 6; no target is analyzed without an authorization record.

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
