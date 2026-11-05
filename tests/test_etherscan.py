from orchestrator.onchain import parse_etherscan_source


def test_single_file():
    r = {"SourceCode": "// SPDX\npragma solidity ^0.8.20;\ncontract C {}",
         "ContractName": "C", "CompilerVersion": "v0.8.20+commit.a1b2c3",
         "OptimizationUsed": "1", "Runs": "200"}
    d = parse_etherscan_source(r)
    assert "C.sol" in d["sources"] and d["compilation"]["name"] == "C"
    assert d["metadata"]["settings"]["optimizer"]["enabled"] is True
    assert d["metadata"]["compiler"]["version"].startswith("v0.8.20")


def test_multifile_double_brace():
    import json
    inner = {"sources": {"contracts/A.sol": {"content": "contract A {}"},
                         "contracts/B.sol": {"content": "contract B {}"}},
             "settings": {"viaIR": True, "remappings": ["@oz/=lib/oz/"]}}
    r = {"SourceCode": "{" + json.dumps(inner) + "}", "ContractName": "A",
         "CompilerVersion": "v0.8.19", "OptimizationUsed": "0", "Runs": "0",
         "EVMVersion": "paris"}
    d = parse_etherscan_source(r)
    assert set(d["sources"]) == {"contracts/A.sol", "contracts/B.sol"}
    assert d["metadata"]["settings"]["viaIR"] is True
    assert d["metadata"]["settings"]["evmVersion"] == "paris"


def test_empty():
    assert parse_etherscan_source({"SourceCode": ""}) is None
