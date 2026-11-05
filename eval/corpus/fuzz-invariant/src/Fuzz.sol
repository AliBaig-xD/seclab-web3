// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
/// Reachable-state bug: a sequence of inc() flips an invariant that must hold.
contract Fuzz {
    uint256 public counter;
    bool public flag;
    function inc() external { counter += 1; if (counter >= 7) flag = true; }
    // Echidna property: must always return true; fuzzer finds the breaking sequence.
    function echidna_flag_never_set() public view returns (bool) { return !flag; }
}
