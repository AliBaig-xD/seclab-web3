from orchestrator.knowledge import KnowledgeBase, HashEmbedder, cosine


def test_cosine():
    assert cosine([1, 0], [1, 0]) == 1.0
    assert abs(cosine([1, 0], [0, 1])) < 1e-9


def test_kb_add_and_retrieve(tmp_path):
    kb = KnowledgeBase(str(tmp_path / "kb.db"), HashEmbedder())
    kb.add("vulnclass", "Reentrancy", "external call before state update lets the callee re-enter withdraw and drain funds")
    kb.add("vulnclass", "Oracle manipulation", "flash loan manipulates spot price to misprice collateral")
    assert kb.count() == 2
    res = kb.query("reentrancy external call re-enter withdraw drain")
    assert res and res[0]["title"] == "Reentrancy"


def test_kb_seed(tmp_path):
    import os
    cards = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge", "cards.json")
    kb = KnowledgeBase(str(tmp_path / "kb.db"))
    n = kb.seed_from_cards(cards)
    assert n >= 10 and kb.count() == n
    hits = kb.query("price oracle flash loan manipulation collateral")
    assert any("Oracle" in h["title"] for h in hits)


def test_researcher_uses_kb_grounding(tmp_path):
    from orchestrator.knowledge import KnowledgeBase
    from orchestrator.researcher import Researcher
    kb = KnowledgeBase(str(tmp_path / "kb.db"))
    kb.add("vulnclass", "Reentrancy", "external call before state update re-enter withdraw drain")
    captured = {}

    class C:
        def generate(self, prompt, system=None):
            captured["prompt"] = prompt
            return "[]"
    Researcher(C(), kb=kb).hypothesize("function withdraw() { msg.sender.call{value:b}(''); balances=0; }")
    assert "Relevant vulnerability knowledge" in captured["prompt"]
    assert "Reentrancy" in captured["prompt"]
