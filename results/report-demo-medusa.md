# Security Report — fuzz-invariant

- Run: `demo-medusa`
- Reportable findings: 1 (PROVEN/CORROBORATED only)

## 1. invariant-violation — PROVEN [HIGH]
- Location: `Fuzz.echidna_flag_never_set`
- Impact: property echidna_flag_never_set falsified; seq: Fuzz.inc() -> Fuzz.inc() -> Fuzz.inc() -> Fuzz.inc() -> Fuzz.inc() -> Fuzz.inc() -> Fuzz.inc()
- Precondition: (fuzzing found a breaking tx sequence)
- Repro: `echidna . --contract Fuzz --test-mode property`
- Evidence:
  - [echidna/echidna] echidna falsified echidna_flag_never_set: Fuzz.inc() -> Fuzz.inc() -> Fuzz.inc() -> Fuzz.inc() -> Fuzz.inc() -> Fuzz.inc() -> Fuzz.inc()
  - [medusa/medusa] medusa: Property Test Fuzz.echidna_flag_never_set() FAILED

---
## Not reported (unproven candidates / falsified)
_Listed for transparency; not shipped as findings._
- solc-version @ `src/Fuzz.sol:2` (CANDIDATE)
- push-zero-opcode @ `src/Fuzz.sol:2` (CANDIDATE)
- state-change-without-event @ `src/Fuzz.sol:7` (CANDIDATE)
- unspecific-solidity-pragma @ `src/Fuzz.sol:2` (CANDIDATE)
- unused-public-function @ `src/Fuzz.sol:9` (CANDIDATE)