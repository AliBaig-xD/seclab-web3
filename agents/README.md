# Agents — roles in the research harness

Coordinated roles the harness (`orchestrator/harness.py`) drives. Each is a real component.

| Agent | Module | Input -> Output | Tools |
|-------|--------|-----------------|-------|
| Orchestrator | harness.py | target -> run dir + findings | all |
| Code intelligence | codeintel.py, kg.py | sources -> call graph, state map, roles, KG | Slither API |
| Protocol intelligence | protocol.py | sources -> invariants/roles/assumptions/questions | LLM |
| Vulnerability hunter | researcher.py | code+hints -> hypotheses | LLM + RAG |
| Swarm (map-reduce) | swarm.py | graph slices -> per-slice + cross-slice hypotheses | LLM + code intel |
| Static scanners | tools/{slither,aderyn,semgrep,differential} | code -> (hypothesis, evidence) | containers |
| Symbolic | tools/{mythril,halmos} | code -> reachability/counterexamples | containers |
| Fuzzers | tools/{echidna,medusa} | code -> falsified properties | containers |
| Exploitation agent | exploit.py | hypothesis -> Foundry PoC (run) | LLM + Foundry sandbox |
| Independent reviewer | reviewer.py | finding -> keep/falsify (never overrides a PoC) | LLM |
| Verifier / correlation | pipeline.py | hypotheses+evidence -> tiered findings | — |
| Reporter | report.py, triage.py, disclosure.py | findings -> report + disclosure | — |

Invariant: the model only proposes; a finding's tier is DERIVED from evidence
(docs/WORKFLOW.md). Nothing is reported without machine evidence or an executable PoC.
