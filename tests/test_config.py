from orchestrator import config


def test_versions_has_model_ref():
    env = config.load_versions()
    assert env["MODEL_REF"].startswith("qwen2.5-coder")


def test_model_config_deterministic():
    m = config.load_model_config()
    assert m["server"] in {"ollama", "vllm", "llamacpp"}
    assert isinstance(m["endpoint"], str) and m["endpoint"]
    assert isinstance(m["model_ref"], str) and m["model_ref"]
    assert m["params"]["temperature"] == 0
    assert m["params"]["seed"] == 0
    assert m["params"]["top_p"] == 1.0
