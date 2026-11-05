# Security Report — reentrancy-etherstore

- Run: `demo-swarm`
- Reportable findings: 2 (PROVEN/CORROBORATED only)

## 1. Reentrancy — PROVEN [HIGH]
- Location: `EtherStore.withdraw`
- Impact: Allows repeated withdrawal of funds before the balance is reset
- Precondition: msg.sender has a non-zero balance
- Repro: `forge test --match-test test_exploit_drains_store`
- Evidence:
  - [llm/swarm] The contract sends Ether to the caller before resetting the balance, creating a reentrancy vulnerability. [slice EtherStore.withdraw]
  - [llm/swarm] The contract sends Ether to the caller before updating the balance, allowing the caller to re-enter the withdraw function and withdraw more 
  - [llm/swarm] The withdraw function calls the external contract (msg.sender) before updating the balance to zero, allowing a reentrancy attack where the u
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
  - [aderyn/aderyn] reentrancy-state-change [HIGH] Reentrancy: State change after external call
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