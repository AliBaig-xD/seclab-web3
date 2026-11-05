# Limitations (honest accounting)

A real lab documents what it cannot (yet) do. ~14 core limitations; every one is
mitigated to some degree and every one can be improved. The hardest is novel-bug
discovery, mitigated primarily by the Phase-9 swarm engine + the trained model.

See the table in the session notes / README. Highest-leverage next levers:
1. **Auto-synthesize fuzz/symbolic harnesses** from protocol-intelligence invariants so
   Echidna/Medusa/Halmos engage on ANY target, not only ones that ship properties. (built)
2. **Halmos counterexample -> deterministic PoC synthesis** (turn symbolic counterexamples
   into runnable PoCs without relying on the LLM, raising PROVEN rate).
3. **DPO/RL on the lab's own verified findings** (train on what actually proved out).
4. Fork-at-block PoC generation for on-chain targets; Etherscan source fallback.
5. Non-root containers + seccomp + network-isolate-after-warmup; injection red-teaming.
6. Larger held-out benchmark; pair Web3Bugs findings with their code; quality-filter data.

Principle that bounds the downside of all limitations: the PROOF GATE. Unproven work is
never reported as a finding, so limitations reduce RECALL, not PRECISION of PROVEN output.
