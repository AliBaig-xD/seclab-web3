from orchestrator import config


def test_versions_has_model_ref():
    env = config.load_versions()
    assert env["MODEL_REF"].startswith("qwen2.5-coder")


def test_model_config_deterministic():
    m = config.load_model_config()
    assert m["server"] == "ollama"
    assert m["params"]["temperature"] == 0
