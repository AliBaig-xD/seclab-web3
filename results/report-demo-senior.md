# Security Report — reentrancy-etherstore

- Run: `demo-senior`
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
  - [aderyn/aderyn] reentrancy-state-change [HIGH] Reentrancy: State change after external call
  - [llm/model] The contract makes an external call to the attacker's address before setting the balance to zero, allowing the attacker to re-enter the withdraw function and withdraw more funds.
  - [foundry_poc/forge] PoC 'test_exploit_drains_store' passed; impact demonstrated on fork

---
## Protocol intelligence
**Invariants:**
- Balances should not decrease before the withdrawal transaction is confirmed.
- The contract should not allow reentrancy attacks.
**Roles / trust boundaries:**
- Depositor
- Withdrawer
**Economic assumptions:**
- Users will not exploit reentrancy vulnerabilities.
- Transactions are processed in the order they are received.
**Adversarial questions:**
- Can an attacker withdraw more funds than they deposited by exploiting reentrancy?
- What happens if the contract is upgraded or modified unexpectedly?
- How can the contract be modified to prevent reentrancy attacks?
---
## Not reported (unproven candidates / falsified)
_Listed for transparency; not shipped as findings._
- solc-version @ `src/EtherStore.sol:2` (CANDIDATE)
- low-level-calls @ `src/EtherStore.sol:8` (CANDIDATE)
- eth-send-unchecked-address @ `src/EtherStore.sol:8` (CANDIDATE)
- push-zero-opcode @ `src/EtherStore.sol:2` (CANDIDATE)
- state-change-without-event @ `src/EtherStore.sol:7` (CANDIDATE)
- unspecific-solidity-pragma @ `src/EtherStore.sol:2` (CANDIDATE)
- low-level-call-with-value @ `src/EtherStore.sol:11` (CANDIDATE)