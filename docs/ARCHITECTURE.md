# seclab-web3 — Architecture

Fully-local EVM security-research lab. A local LLM proposes hypotheses; proven tools
verify; nothing is a "finding" without machine evidence or an executable PoC.

## Data flow
```
target (local repo | on-chain addr)
  -> ingest (Sourcify fetch + compile, or local)            orchestrator/ingest.py, onchain.py
  -> code intelligence (Slither call graph/state/roles)     orchestrator/codeintel.py
  -> hypotheses:
       static scanners  (Slither, Aderyn, Semgrep)          orchestrator/tools/*
       LLM researcher   (14B, RAG-grounded)                 orchestrator/researcher.py, knowledge.py
       swarm map-reduce (graph slices + cross-slice)        orchestrator/swarm.py
       protocol intel   (invariants, roles, questions)      orchestrator/protocol.py
  -> correlation (family + contract stem)                   orchestrator/pipeline.py
  -> verification:
       symbolic (Mythril, Halmos)   fuzz (Echidna, Medusa)  orchestrator/tools/*
       exploitation agent -> Foundry PoC on a fork          orchestrator/exploit.py
  -> tier (derived from evidence) + adversarial reviewer    orchestrator/schema.py, reviewer.py
  -> triage + proof-gated report                            orchestrator/triage.py, report.py
```

## Proof gate (the core invariant)
A Finding's tier is DERIVED from evidence, never asserted by the model:
- **PROVEN** = a dynamic execution proof (Foundry PoC, or Echidna/Medusa falsification) + a repro.
- **CORROBORATED** = >=2 independent tools agree.
- **CANDIDATE** = single tool / LLM-only -> NEVER reported.
Only PROVEN + CORROBORATED reach the report. The reviewer may demote, never a PoC.

## Components
Orchestrator/pipeline, code intelligence, protocol intelligence, vulnerability hunter
(LLM + swarm), independent reviewer, validation lab (static/symbolic/fuzz/PoC), RAG KB,
reporting/triage, authorization gate, training pipeline. See docs/IMPLEMENTATION_PLAN.md.

## Runtime
Everything on EC2. Tools run in the pinned analysis container (the sandbox). The model
serves from an Ollama container (GPU). Training frees the GPU (stops inference) and runs
in /opt/dlami/nvme/seclab/trainvenv.
