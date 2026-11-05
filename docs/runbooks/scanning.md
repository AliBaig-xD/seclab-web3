# Runbook — Scanning a target

All commands run on the box: `cd ~/seclab-web3`. Entry point: `python3 -m orchestrator.cli`.

## Local repo
```
python3 -m orchestrator.cli scan <dir> [--llm] [--swarm] [--rag] [--exploit] [--fast] \
    [--poc-test <t> --poc-family <f>] [--run-id <id>]
```
- `--fast` skips the slow symbolic/fuzz engines (static + PoC only).
- `--llm` enables the live researcher + reviewer + protocol intelligence.
- `--swarm` enables graph-sliced map-reduce hunting (supersedes single-shot researcher).
- `--rag` grounds the hunter in the vuln knowledge base.
- `--exploit` lets the LLM generate + run Foundry PoCs to prove candidates.
- `--poc-test/--poc-family` confirms a known exploit test as PROVEN (demo/regression).

The target MUST have an authorization record in `config/authorization.yaml` (id = basename).

## On-chain (deployed) target
```
python3 -m orchestrator.cli scan --onchain 0x<addr> --chain 1 --basis bounty:<program> [...]
```
Fetches verified source (Sourcify), compiles, and runs the pipeline. `--basis` asserts
authorization (own | bounty:<p> | engagement:<id>). PoCs run only on a sandboxed fork.

## Output
A Markdown report at `results/report-<run-id>.md` (PROVEN/CORROBORATED only; candidates
and falsified items in a transparency appendix) + the evidence DB at `results/evidence.db`.

## Benchmark (lab quality)
`python3 -m orchestrator.labeval` (full) or `--fast` -> `results/benchmark_report.json`
(recall on known vulns, false positives on the clean control, PoC-repro count).
