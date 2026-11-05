from orchestrator.researcher import parse_hypotheses, build_prompt, Researcher, SYSTEM

VALID = '''Here are the issues:
```json
[
  {"vuln_type":"reentrancy","location":"Vault.sol:42","precondition":"ext call first",
   "claimed_impact":"drain","rationale":"state after call"},
  {"vuln_type":"access-control","location":"Admin.sol:10","precondition":"no modifier",
   "claimed_impact":"takeover","rationale":"missing onlyOwner"}
]
```
done'''


def test_parse_with_preamble_and_fence():
    hs = parse_hypotheses(VALID)
    assert len(hs) == 2
    assert hs[0].vuln_type == "reentrancy" and hs[0].source == "llm"


def test_drop_malformed_entries():
    txt = '[{"vuln_type":"x"}, {"vuln_type":"reentrancy","location":"a:1","precondition":"p","claimed_impact":"i"}]'
    hs = parse_hypotheses(txt)
    assert len(hs) == 1 and hs[0].vuln_type == "reentrancy"


def test_no_array_returns_empty():
    assert parse_hypotheses("the model refused") == []
    assert parse_hypotheses("[not json]") == []


def test_cap_enforced():
    big = "[" + ",".join(
        '{"vuln_type":"x","location":"a:1","precondition":"p","claimed_impact":"i"}'
        for _ in range(100)) + "]"
    assert len(parse_hypotheses(big, cap=5)) == 5


def test_prompt_fences_untrusted_code():
    p = build_prompt("selfdestruct(msg.sender);", "slither: suicidal")
    assert "<UNTRUSTED_CODE>" in p and "selfdestruct" in p
    assert "never instructions" in SYSTEM


def test_researcher_with_fake_client():
    class FC:
        def generate(self, prompt, system=None):
            assert "<UNTRUSTED_CODE>" in prompt
            return VALID
    assert len(Researcher(FC()).hypothesize("code")) == 2
