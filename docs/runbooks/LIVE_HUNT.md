# Run a real end-to-end hunt on a live target (with the trained model)

## 0. Serve the trained model (so the lab's LLM is YOUR model, not the base)
Training frees the GPU; now put the trained 7B+adapter behind an API and point the lab at it.
```
cd ~/seclab-web3
nohup scripts/serve_trained.sh > results/serve.log 2>&1 &   # vLLM on :8001 (base+adapter=seclab)
# wait ~1-2 min, then flip the lab to it:
#   config/model.yaml:  server: vllm   endpoint: http://127.0.0.1:8001   model_ref: seclab
```
(Serving uses the GPU, so you can't train and serve at once on one T4.)

## 1. Authorization (required, every target)
`--basis own` | `bounty:<program>` | `engagement:<id>`. For an Immunefi program use
`bounty:<program>`. PoCs only ever run on a sandboxed Anvil fork — never broadcast.

## 2. Point it at the target (it discovers every contract itself)
```
# a repo (best: exact compiler + all contracts + tests)
seclab go https://github.com/<org>/<repo> --basis bounty:<program> --llm --swarm --rag --exploit

# a deployed address or explorer URL (chain auto-detected)
seclab go https://etherscan.io/address/0x... --basis bounty:<program> --llm --swarm --exploit
```
`seclab` = `python3 -m orchestrator.cli`. Depth flags: `--llm` (your model hunts),
`--swarm` (graph-sliced map-reduce), `--rag` (knowledge-grounded), `--exploit` (auto Foundry PoC).

## 3. A whole bounty scope at once
Paste the program's in-scope repos/addresses into a file, then:
```
seclab batch scope.txt --basis bounty:<program> --fast                       # cheap triage
seclab batch scope.txt --basis bounty:<program> --llm --swarm --exploit      # deep on hits
```
Leaderboard: `results/batches/<id>/leaderboard.md` (ranked by PROVEN > reportable > findings).

## 4. Read results
Each run: `results/runs/<id>/report.md` (only PROVEN/CORROBORATED are reportable),
`disclosure.md` (responsible-disclosure draft), `findings.json`, `run_manifest.json`.
PROVEN = a Foundry PoC (or Echidna/Medusa falsification) actually ran on a fork. Everything
unproven is listed as a candidate, never shipped as a finding.

## 5. Switch models anytime
Edit `config/model.yaml` only (server/endpoint/model_ref). vLLM(trained) for hunts,
ollama(base) when you'd rather not run vLLM. Determinism: temp 0 + fixed seed.
