// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
/// Correctly written: checks-effects-interactions + reentrancy guard. Negative control.
contract SafeVault {
    mapping(address => uint256) public balances;
    bool private locked;
    modifier nonReentrant() { require(!locked, "reentrant"); locked = true; _; locked = false; }
    function deposit() external payable { balances[msg.sender] += msg.value; }
    function withdraw() external nonReentrant {
        uint256 b = balances[msg.sender];
        require(b > 0, "no balance");
        balances[msg.sender] = 0;                      // effects before interaction
        (bool ok, ) = msg.sender.call{value: b}("");
        require(ok, "send failed");
    }
}
