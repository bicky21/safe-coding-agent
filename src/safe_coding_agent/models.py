"""Chat model providers.

A model is written as "provider:model-name":

    ollama:gemma3:4b                  local, free (needs Ollama running)
    openai:gpt-4o-mini                OpenAI, or any OpenAI-compatible API with --base-url
                                      (Groq, OpenRouter, Gemini, LM Studio, vLLM, ...)
    anthropic:claude-sonnet-5-5       Anthropic Claude (needs ANTHROPIC_API_KEY)

Other providers can be added with register_provider().
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable

from langchain_core.language_models.chat_models import BaseChatModel


class ModelError(RuntimeError):
    """The model can't be created or reached; the message says how to fix it."""


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    name: str
    base_url: str | None = None
    api_key_env: str | None = None
    max_tokens: int = 8192

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.name}"


def parse_model(spec: str, base_url: str | None = None, api_key_env: str | None = None,
                max_tokens: int = 8192) -> ModelSpec:
    if ":" not in spec:
        raise ModelError(f"model must look like 'provider:name' (e.g. ollama:gemma3:4b), not {spec!r}")
    provider, name = spec.split(":", 1)
    provider = provider.strip().lower()
    if provider not in _PROVIDERS:
        raise ModelError(f"unknown provider {provider!r}; choose one of: {', '.join(sorted(_PROVIDERS))}")
    if not name.strip():
        raise ModelError(f"no model name after '{provider}:'")
    return ModelSpec(provider, name.strip(), base_url, api_key_env, max_tokens)


def _need(package: str, extra: str):
    raise ModelError(f"the '{extra}' provider needs an extra package. Install it with:\n"
                     f"    pip install \"safe-coding-agent[{extra}]\"      (or: pip install {package})")


def _ollama(spec: ModelSpec, temperature: float) -> BaseChatModel:
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        _need("langchain-ollama", "ollama")
    kwargs = {"model": spec.name, "temperature": temperature, "num_predict": spec.max_tokens}
    if spec.base_url or os.environ.get("OLLAMA_HOST"):
        kwargs["base_url"] = spec.base_url or os.environ["OLLAMA_HOST"]
    if os.environ.get("SCA_OLLAMA_NUM_CTX"):
        kwargs["num_ctx"] = int(os.environ["SCA_OLLAMA_NUM_CTX"])
    return ChatOllama(**kwargs)


def _openai(spec: ModelSpec, temperature: float) -> BaseChatModel:
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        _need("langchain-openai", "openai")
    key_env = spec.api_key_env or "OPENAI_API_KEY"
    kwargs = {"model": spec.name, "temperature": temperature, "max_tokens": spec.max_tokens,
              "api_key": os.environ.get(key_env) or "not-needed"}
    base_url = spec.base_url or os.environ.get("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def _anthropic(spec: ModelSpec, temperature: float) -> BaseChatModel:
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        _need("langchain-anthropic", "anthropic")
    key_env = spec.api_key_env or "ANTHROPIC_API_KEY"
    kwargs = {"model": spec.name, "temperature": temperature, "max_tokens": spec.max_tokens}
    if os.environ.get(key_env):
        kwargs["api_key"] = os.environ[key_env]
    if spec.base_url:
        kwargs["base_url"] = spec.base_url
    return ChatAnthropic(**kwargs)


_PROVIDERS: dict[str, Callable[[ModelSpec, float], BaseChatModel]] = {
    "ollama": _ollama,
    "openai": _openai,
    "anthropic": _anthropic,
}


def register_provider(name: str, factory: Callable[[ModelSpec, float], BaseChatModel]) -> None:
    """Add a provider: factory(spec, temperature) -> a LangChain chat model."""
    _PROVIDERS[name.lower()] = factory


def make_model(spec: ModelSpec, temperature: float) -> BaseChatModel:
    return _PROVIDERS[spec.provider](spec, temperature)


def preflight(spec: ModelSpec) -> None:
    """Fail early with a clear fix if the model obviously can't work."""
    if spec.provider == "ollama":
        try:
            import ollama
        except ImportError:
            _need("langchain-ollama", "ollama")
        host = spec.base_url or os.environ.get("OLLAMA_HOST")
        client = ollama.Client(host=host) if host else ollama.Client()
        try:
            client.show(spec.name)
        except Exception as e:  # noqa: BLE001 - ollama raises several error types
            if "not found" in str(e).lower():
                raise ModelError(f"model '{spec.name}' is not downloaded in Ollama.\n"
                                 f"Fix:  ollama pull {spec.name}      (list models: ollama list)") from e
            raise ModelError(f"can't reach Ollama ({e}).\nFix:  start it with: ollama serve") from e
    elif spec.provider == "anthropic":
        key = spec.api_key_env or "ANTHROPIC_API_KEY"
        if not os.environ.get(key):
            raise ModelError(f"set your Anthropic API key first:  export {key}=sk-ant-...")
        make_model(spec, 0.0)
    elif spec.provider == "openai":
        key = spec.api_key_env or "OPENAI_API_KEY"
        if not os.environ.get(key) and not (spec.base_url or os.environ.get("OPENAI_BASE_URL")):
            raise ModelError(f"set your API key first:  export {key}=...   "
                             "(or pass --base-url for a local OpenAI-compatible server)")
        make_model(spec, 0.0)


def message_text(message) -> str:
    """Plain text of a chat model reply (handles providers that return content blocks)."""
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content)


_RETRYABLE = ("rate limit", "rate_limit", "overloaded", "429", "500", "502", "503", "504",
              "timeout", "timed out", "temporarily", "connection reset", "connection aborted")


def invoke_with_retry(model: BaseChatModel, messages, retries: int = 4, base_delay: float = 2.0) -> str:
    """Call the model; retry temporary failures (rate limits, overload, network) with backoff."""
    for attempt in range(retries + 1):
        try:
            return message_text(model.invoke(messages))
        except Exception as e:  # noqa: BLE001 - providers raise many error types
            text = f"{type(e).__name__}: {e}".lower()
            if attempt == retries or not any(k in text for k in _RETRYABLE):
                raise ModelError(f"model call failed: {e}") from e
            time.sleep(base_delay * (2 ** attempt))
    raise AssertionError("unreachable")
