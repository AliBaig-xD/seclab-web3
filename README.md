# seclab-web3

A fully-local, production-grade EVM security-research lab. A local LLM proposes
hypotheses; proven tools verify; **nothing is a "finding" without machine evidence or an
executable PoC.** Built to make a small model + small hardware punch far above their
weight through engineering and a large curated dataset.

## Quick start (on the box)
`seclab` = `python3 -m orchestrator.cli`. **Point it at a target; it discovers every
contract itself.** Engine flags (not the target) set the depth and runtime.
```
# ONE target — paste anything: repo URL | explorer URL | address | local path
seclab go https://github.com/org/protocol --basis bounty:<p> --llm --swarm --exploit
seclab go https://etherscan.io/address/0x<addr>      # chain auto-detected from the URL
seclab go 0x<addr> --chain 1 --fast                  # fast = static-only triage (seconds)

# MANY targets — harvest a corpus, scan it, read the ranked leaderboard
seclab targets --chain 1 --limit 500 --out corpus.txt            # gather, do not hand-pick
seclab targets --chain 1 --solc-below 0.6.0 --out old.txt        # old-era (pre-2020) contracts
seclab batch corpus.txt --basis bounty:<p> --fast                # triage, then go deep on hits
seclab batch old.txt   --basis bounty:<p> --llm --swarm --exploit

seclab benchmark   # recall / FP / PoC-repro      seclab kg <dir>   # knowledge graph
bash scripts/train.sh   # train the specialized model
```
Depth: `--fast` (static, seconds) · default (+symbolic+fuzz, minutes) ·
`--llm --swarm --rag --exploit` (AI hunter + auto-PoC, minutes–hours). Full guide:
**docs/runbooks/USAGE.md**. Every run writes `results/runs/<id>/` (report.md,
disclosure.md, findings.json, kg.db, evidence.db, run_manifest.json); batches write
`results/batches/<id>/leaderboard.{md,json}`.

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
- **On-chain ingestion**: paste an address or a block-explorer URL (Sourcify V2 + Etherscan
  v2 fallback, chain auto-detected) with exact compiler settings; PoCs on Anvil forks.
- **Batch + harvest**: scan a whole corpus into a ranked leaderboard; harvest candidate
  lists (by chain, solc era, or deploy date) so targets are gathered, not hand-picked.
- **Training pipeline**: multi-source curated dataset (SmartBugs, SolidiFI, 644 real
  DeFiHackLabs PoCs, Web3Bugs, DeFiVulnLabs, not-so-smart, our corpus, self-labeling
  flywheel), completion-masked QLoRA SFT, eval/ckpt/resume, config-scalable, HF push.
- **Knowledge base**: RAG + a vuln-class corpus spanning every EVM domain.

## Docs
`docs/ARCHITECTURE.md` · `docs/WORKFLOW.md` (the law) · `docs/IMPLEMENTATION_PLAN.md` ·
`docs/runbooks/USAGE.md` (end-user guide) · `docs/runbooks/` (scanning, training,
operations, on-chain) · `RESUME.md` (current state) ·
`SCOPE.md` · `agents/README.md`.
