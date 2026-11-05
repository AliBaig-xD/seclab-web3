// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract CheckMath {
    function add(uint256 a, uint256 b) internal pure returns (uint256) {
        unchecked { return a + b; }   // intentional overflow
    }
    function check_add_no_overflow(uint256 a, uint256 b) public pure {
        assert(add(a, b) >= a);       // halmos finds overflow counterexample
    }
    function check_add_commutes(uint256 a, uint256 b) public pure {
        assert(add(a, b) == add(b, a)); // holds -> PASS (control)
    }
}
