// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// Classic reentrancy: external call occurs BEFORE the balance is zeroed.
contract EtherStore {
    mapping(address => uint256) public balances;
    function deposit() external payable { balances[msg.sender] += msg.value; }
    function withdraw() external {
        uint256 bal = balances[msg.sender];
        require(bal > 0, "no balance");
        (bool ok, ) = msg.sender.call{value: bal}(""); // reentrancy point
        require(ok, "send failed");
        balances[msg.sender] = 0;                       // state update AFTER call
    }
}
