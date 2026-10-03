import importlib


def test_module_is_importable(monkeypatch):
    # steps.summarize builds its LLM at import time, which requires an API key.
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")

    module = importlib.import_module(
        "companion.endpoint.readit.app.update_summary_model"
    )

    assert callable(module.main)
