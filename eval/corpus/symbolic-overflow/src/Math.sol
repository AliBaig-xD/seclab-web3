// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Math {
    function add(uint256 a, uint256 b) external pure returns (uint256) {
        unchecked { return a + b; }   // intentional: can overflow
    }
}
