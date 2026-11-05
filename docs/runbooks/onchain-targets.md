# Runbook — Live / on-chain targets

The authorization model is target-agnostic but enforced: no target is processed without
an affirmed record, and PoCs ALWAYS run on a sandboxed fork, never broadcast.

## Flow
1. Confirm you are authorized (own code | a bounty whose scope permits automated testing |
   a written engagement).
2. `python3 -m orchestrator.cli scan --onchain 0x<addr> --chain <id> --basis <basis>`
   - fetches verified source (Sourcify V2), reconstructs a Foundry project with the exact
     compiler settings (optimizer/viaIR/evmVersion), and runs the pipeline.
3. For exploit validation, the lab forks the chain at a block (`anvil --fork-url`) and runs
   the PoC against the fork copy. No mainnet transaction is ever sent.

Supported chains: any Sourcify-indexed EVM chain (pass `--chain <id>`). If a contract is
not verified on Sourcify, provide the source locally instead.
