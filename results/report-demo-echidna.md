# Security Report — fuzz-invariant

- Run: `demo-echidna`
- Reportable findings: 0 (PROVEN/CORROBORATED only)

_No proof-gated findings._
---
## Not reported (unproven candidates / falsified)
_Listed for transparency; not shipped as findings._
- solc-version @ `src/Fuzz.sol:2` (CANDIDATE)
- push-zero-opcode @ `src/Fuzz.sol:2` (CANDIDATE)
- state-change-without-event @ `src/Fuzz.sol:7` (CANDIDATE)
- unspecific-solidity-pragma @ `src/Fuzz.sol:2` (CANDIDATE)
- unused-public-function @ `src/Fuzz.sol:9` (CANDIDATE)
- invariant-violation @ `Fuzz.echidna_flag_never_set` (CANDIDATE)