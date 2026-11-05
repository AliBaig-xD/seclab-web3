# Security Report — reentrancy-etherstore

- Run: `demo-llm`
- Reportable findings: 2 (PROVEN/CORROBORATED only)

## 1. Reentrancy — PROVEN [HIGH]
- Location: `EtherStore.sol:withdraw`
- Impact: The attacker can repeatedly withdraw funds from the contract until it is drained.
- Precondition: An attacker has a balance in the contract and can execute the withdraw function.
- Repro: `forge test --match-test test_exploit_drains_store`
- Evidence:
  - [llm/model] The contract sends Ether to the caller before setting the balance to zero, allowing the caller to re-enter the withdraw function and withdraw more Ether.
  - [foundry_poc/forge] PoC 'test_exploit_drains_store' passed; impact demonstrated on fork

## 2. reentrancy — PROVEN [HIGH]
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