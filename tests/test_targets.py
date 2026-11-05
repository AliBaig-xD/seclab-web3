from orchestrator.targets import resolve_target

W = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"


def test_raw_address():
    assert resolve_target(W) == {"kind": "address", "address": W, "chain": None}


def test_explorer_urls():
    r = resolve_target(f"https://etherscan.io/address/{W}")
    assert r["kind"] == "explorer" and r["address"] == W and r["chain"] == 1
    assert resolve_target(f"https://arbiscan.io/address/{W}")["chain"] == 42161
    assert resolve_target(f"https://basescan.org/token/{W}")["chain"] == 8453


def test_repo_and_local_and_dapp():
    assert resolve_target("https://github.com/foundry-rs/forge-template")["kind"] == "repo"
    assert resolve_target("git@github.com:org/repo.git")["kind"] == "repo"
    assert resolve_target("./my-protocol")["kind"] == "local"
    assert resolve_target("https://app.uniswap.org")["kind"] == "dapp"
