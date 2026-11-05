import json, tempfile, os
from orchestrator import batch, targets


def test_parse_targets_file():
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("# comment\n")
        f.write("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 1\n")
        f.write("\n")
        f.write("https://arbiscan.io/address/0xabc  # trailing comment\n")
        f.write("./local/path\n")
        f.write("0xdAC17F958D2ee523a2206206994597C13D831ec7, 137\n")
        p = f.name
    rows = batch.parse_targets_file(p)
    os.unlink(p)
    assert rows[0] == ("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1)
    assert rows[1][0].startswith("https://arbiscan.io") and rows[1][1] is None
    assert rows[2] == ("./local/path", None)
    assert rows[3] == ("0xdAC17F958D2ee523a2206206994597C13D831ec7", 137)


def test_slug_bounded():
    assert len(batch._slug("0x" + "a" * 60)) <= 36
    assert batch._slug("!!!") == "t"


def test_harvest_pagination(monkeypatch):
    pages = [
        {"results": [{"address": f"0x{i:040x}", "matchId": str(i)} for i in range(200)]},
        {"results": [{"address": f"0x{i:040x}", "matchId": str(i)} for i in range(200, 260)]},
    ]
    calls = {"n": 0}

    def fake(url, timeout=30):
        i = calls["n"]
        calls["n"] += 1
        return pages[i] if i < len(pages) else {"results": []}

    monkeypatch.setattr(targets, "_get_json", fake)
    got = targets.harvest_targets(chain=1, limit=250, out=None)
    assert len(got) == 250 and got[0] == "0x" + "0" * 40


def test_harvest_date_filter(monkeypatch):
    monkeypatch.setenv("ETHERSCAN_API_KEY", "k")
    monkeypatch.setattr(targets, "_get_json",
                        lambda u, timeout=30: {"results": [{"address": f"0x{i:040x}", "matchId": str(i)}
                                                           for i in range(50)]})
    # half deployed in 2018, half in 2024
    monkeypatch.setattr(targets, "_deploy_ts",
                        lambda ch, a, k: 1514764800 if int(a, 16) % 2 == 0 else 1704067200)
    monkeypatch.setattr(targets._time, "sleep", lambda *a: None)
    got = targets.harvest_targets(chain=1, limit=10, before="2020-01-01", out=None)
    assert got and all(int(a, 16) % 2 == 0 for a in got)  # only pre-2020 kept
