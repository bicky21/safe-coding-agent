import pytest

from safe_coding_agent.models import ModelError, invoke_with_retry, message_text, parse_model


class Flaky:
    def __init__(self, errors):
        self.errors = list(errors)
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return type("Msg", (), {"content": "ok"})()


def test_retries_temporary_errors():
    m = Flaky([RuntimeError("429 rate limit"), RuntimeError("503 overloaded")])
    assert invoke_with_retry(m, [], base_delay=0) == "ok" and m.calls == 3


def test_does_not_retry_real_errors():
    m = Flaky([RuntimeError("invalid api key")])
    with pytest.raises(ModelError, match="invalid api key"):
        invoke_with_retry(m, [], base_delay=0)
    assert m.calls == 1


def test_gives_up_after_retries():
    m = Flaky([RuntimeError("timeout")] * 10)
    with pytest.raises(ModelError):
        invoke_with_retry(m, [], retries=2, base_delay=0)
    assert m.calls == 3


def test_message_text_handles_content_blocks():
    msg = type("Msg", (), {"content": [{"type": "text", "text": "a"}, {"type": "tool_use"}, "b"]})()
    assert message_text(msg) == "ab"


@pytest.mark.parametrize("spec, error", [("gemma3", "provider:name"), ("nope:x", "unknown provider"),
                                         ("ollama:", "no model name")])
def test_bad_specs(spec, error):
    with pytest.raises(ModelError, match=error):
        parse_model(spec)


def test_model_name_may_contain_colons():
    s = parse_model("ollama:gemma3:4b")
    assert (s.provider, s.name, s.label) == ("ollama", "gemma3:4b", "ollama:gemma3:4b")


def test_context_for_rounds_to_fixed_sizes(monkeypatch):
    from safe_coding_agent.models import context_for
    monkeypatch.delenv("SCA_OLLAMA_MAX_CTX", raising=False)
    assert context_for(1000) == (8192, True)            # 333 tokens + 4096 reply reserve
    assert context_for(40_000)[0] == 32768
    assert context_for(1_000_000) == (32768, False)      # too big for the default limit
    monkeypatch.setenv("SCA_OLLAMA_MAX_CTX", "131072")
    assert context_for(1_000_000) == (131072, False)
    assert context_for(200_000) == (131072, True)


def test_ollama_num_ctx_passed_through(monkeypatch):
    from safe_coding_agent.models import make_model
    monkeypatch.delenv("SCA_OLLAMA_NUM_CTX", raising=False)
    m = make_model(parse_model("ollama:gemma3:4b").__class__(**{**parse_model("ollama:gemma3:4b").__dict__,
                                                               "num_ctx": 16384}), 0.0)
    assert m.num_ctx == 16384
    monkeypatch.setenv("SCA_OLLAMA_NUM_CTX", "4096")                    # a fixed value always wins
    assert make_model(parse_model("ollama:gemma3:4b"), 0.0).num_ctx == 4096


def test_default_code_budget_fits_ollama():
    from safe_coding_agent.agent import Settings
    from safe_coding_agent.models import context_for
    s = Settings(model=parse_model("ollama:gemma3:4b"))
    assert context_for(s.code_budget + 12_000)[1]
    assert Settings(model=parse_model("anthropic:claude-sonnet-5-5")).code_budget == 120_000


def test_ollama_num_thread_from_env(monkeypatch):
    from safe_coding_agent.models import make_model
    monkeypatch.setenv("SCA_OLLAMA_NUM_THREAD", "4")
    assert make_model(parse_model("ollama:qwen2.5-coder:7b"), 0.0).num_thread == 4


@pytest.mark.parametrize("value, message", [(None, "is not set"), ("", "is empty"), (" gsk_x", "space")])
def test_preflight_catches_bad_api_keys(monkeypatch, value, message):
    from safe_coding_agent.models import preflight
    if value is None:
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
    else:
        monkeypatch.setenv("GROQ_API_KEY", value)
    spec = parse_model("openai:llama-3.3-70b-versatile", base_url="https://api.groq.com/openai/v1",
                       api_key_env="GROQ_API_KEY")
    with pytest.raises(ModelError, match=message):
        preflight(spec)


def test_preflight_local_openai_server_needs_no_key(monkeypatch):
    from safe_coding_agent.models import preflight
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    preflight(parse_model("openai:local-model", base_url="http://localhost:1234/v1"))   # no error


def test_preflight_good_key(monkeypatch):
    from safe_coding_agent.models import preflight
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    preflight(parse_model("openai:x", base_url="https://api.groq.com/openai/v1", api_key_env="GROQ_API_KEY"))
