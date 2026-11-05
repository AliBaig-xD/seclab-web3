from orchestrator.protocol import parse_protocol_json, ProtocolIntelligence


def test_parse_protocol():
    txt = 'notes {"invariants":["sum==total"],"roles":["owner"],"assumptions":["oracle fresh"],"questions":["stale oracle?"]} end'
    m = parse_protocol_json(txt)
    assert m["invariants"] == ["sum==total"]
    assert m["questions"] == ["stale oracle?"]
    assert m["roles"] == ["owner"]


def test_parse_protocol_empty():
    assert parse_protocol_json("no json") == {"invariants": [], "roles": [], "assumptions": [], "questions": []}


def test_protocol_intelligence_with_fake_client():
    class C:
        def generate(self, p, system=None):
            return '{"invariants":["x"],"roles":[],"assumptions":[],"questions":["q?"]}'
    m = ProtocolIntelligence(C()).analyze("code")
    assert m["invariants"] == ["x"] and m["questions"] == ["q?"]
