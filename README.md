# seclab-web3

A fully-local, production-grade EVM security-research lab. A local LLM proposes
hypotheses; proven tools verify; **nothing is a "finding" without machine evidence or an
executable PoC.** Built to make a small model + small hardware punch far above their
weight through engineering and a large curated dataset.

## Quick start (on the box)
```
python3 -m orchestrator.cli scan <dir> --llm --swarm --rag --exploit      # full agentic run
python3 -m orchestrator.cli onchain 0x<addr> --chain 1 --basis bounty:<p> # deployed contract
python3 -m orchestrator.cli benchmark        # recall / FP / PoC-repro
python3 -m orchestrator.cli kg <dir>         # knowledge graph of a target
bash scripts/train.sh                        # train the specialized model
```
Every run writes `results/runs/<id>/` with report.md, disclosure.md, findings.json,
kg.db, evidence.db, run.log, run_manifest.json.

## The invariant (docs/WORKFLOW.md)
A Finding's tier is DERIVED from evidence, never asserted by the model:
- **PROVEN** = dynamic execution proof (Foundry PoC, or Echidna/Medusa falsification) + repro.
- **CORROBORATED** = >=2 independent tools agree.
- **CANDIDATE** = single tool / LLM-only -> never reported.

## What's inside
- **Validation lab**: Slither, Aderyn, Semgrep (static) · Mythril, Halmos (symbolic) ·
  Echidna, Medusa (fuzz) · Foundry PoC · differential testing.
- **Agentic harness**: orchestrator, code intelligence (+KG), protocol intelligence,
  LLM hunter (RAG-grounded), **swarm map-reduce engine** (graph slices -> per-slice hunts
  -> cross-slice consolidation), exploitation agent, independent reviewer, triage, report,
  responsible disclosure.
- **On-chain ingestion** (Sourcify V2) with exact compiler settings; PoCs on Anvil forks.
- **Training pipeline**: multi-source curated dataset (SmartBugs, SolidiFI, 644 real
  DeFiHackLabs PoCs, Web3Bugs, DeFiVulnLabs, not-so-smart, our corpus, self-labeling
  flywheel), completion-masked QLoRA SFT, eval/ckpt/resume, config-scalable, HF push.
- **Knowledge base**: RAG + a vuln-class corpus spanning every EVM domain.

## Docs
`docs/ARCHITECTURE.md` · `docs/WORKFLOW.md` (the law) · `docs/IMPLEMENTATION_PLAN.md` ·
`docs/runbooks/` (scanning, training, operations, on-chain) · `RESUME.md` (current state) ·
`SCOPE.md` · `agents/README.md`.
