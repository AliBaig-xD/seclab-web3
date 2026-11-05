from orchestrator.tools.medusa import parse_medusa_text

SAMPLE = "\x1b[32m[FAILED]\x1b[0m Property Test: Fuzz.echidna_flag_never_set()\n[PASSED] Assertion Test: Fuzz.inc()\n"


def test_parse_medusa():
    r = parse_medusa_text(SAMPLE)
    assert r["Fuzz.echidna_flag_never_set()"]["failed"] is True
    assert r["Fuzz.inc()"]["failed"] is False


def test_parse_medusa_empty():
    assert parse_medusa_text("nothing") == {}
