from orchestrator.tools.echidna import parse_echidna_text

SAMPLE = """[Worker 0] Test echidna_flag_never_set falsified!
  Call sequence:
Fuzz.inc() from: 0x1 Time delay: 1 seconds
Fuzz.inc() from: 0x2 Time delay: 1 seconds
[Worker 1] Test echidna_balance_ok passing
"""


def test_parse_echidna():
    r = parse_echidna_text(SAMPLE)
    assert r["echidna_flag_never_set"]["falsified"] is True
    assert "Fuzz.inc()" in r["echidna_flag_never_set"]["sequence"]
    assert r["echidna_balance_ok"]["falsified"] is False


def test_parse_echidna_empty():
    assert parse_echidna_text("no tests here") == {}
