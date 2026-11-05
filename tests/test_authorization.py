import pytest, textwrap
from orchestrator.authorization import ScopeGate, AuthorizationError

AUTH = textwrap.dedent("""
targets:
  - id: repoA
    basis: own
    poc_allowed: true
    affirmed_by: dev@archrco.com
  - id: repoB
    basis: "bounty:immunefi-x"
    poc_allowed: false
    affirmed_by: dev@archrco.com
  - id: repoC
    basis: bogus
    poc_allowed: true
    affirmed_by: dev@archrco.com
  - id: repoD
    basis: own
    poc_allowed: true
""")


def gate(tmp_path):
    p = tmp_path / "auth.yaml"
    p.write_text(AUTH)
    return ScopeGate(str(p))


def test_missing_record(tmp_path):
    with pytest.raises(AuthorizationError):
        gate(tmp_path).assert_authorized("nope")


def test_own_allows_poc(tmp_path):
    assert gate(tmp_path).assert_authorized("repoA", poc=True)["id"] == "repoA"


def test_static_ok_but_poc_denied(tmp_path):
    g = gate(tmp_path)
    g.assert_authorized("repoB", poc=False)
    with pytest.raises(AuthorizationError):
        g.assert_authorized("repoB", poc=True)


def test_bad_basis_rejected(tmp_path):
    with pytest.raises(AuthorizationError):
        gate(tmp_path).assert_authorized("repoC")


def test_unaffirmed_rejected(tmp_path):
    with pytest.raises(AuthorizationError):
        gate(tmp_path).assert_authorized("repoD")
