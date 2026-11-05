# Security Report — reentrancy-etherstore

- Run: `demo-reentrancy`
- Reportable findings: 1 (PROVEN/CORROBORATED only)

## 1. reentrancy — PROVEN [HIGH]
- Location: `src/EtherStore.sol:8`
- Impact: Reentrancy in EtherStore.withdraw() (src/EtherStore.sol#8-14):
	External calls:
	- (ok,None) = msg.sender.call{value: bal}() (src/EtherStore.sol#11)
	State variables written after the call(s):
	- bala
- Precondition: (surfaced by slither detector)
- Repro: `forge test --match-test test_exploit_drains_store`
- Evidence:
  - [slither/slither] reentrancy-eth [High] Reentrancy in EtherStore.withdraw() (src/EtherStore.sol#8-14):
	External calls:
	- (ok,None) = msg.sender.call{value: ba
  - [foundry_poc/forge] PoC 'test_exploit_drains_store' passed; impact demonstrated on fork

---
## Not reported (unproven candidates / falsified)
_Listed for transparency; not shipped as findings._
- solc-version @ `src/EtherStore.sol:2` (CANDIDATE)
- low-level-calls @ `src/EtherStore.sol:8` (CANDIDATE)