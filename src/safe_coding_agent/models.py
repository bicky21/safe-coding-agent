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
import re
import time
from dataclasses import dataclass
from typing import Callable

from langchain_core.language_models.chat_models import BaseChatModel


class ModelError(RuntimeError):
    """The model can't be created or reached; the message says how to fix it."""

    @property
    def too_large(self) -> bool:
        """The request (prompt + reserved answer length) is over a size or tokens-per-minute limit."""
        text = str(self).lower()
        return ("413" in text or "request too large" in text or "context_length_exceeded" in text
                or "maximum context length" in text or "max_tokens" in text and "too" in text)


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    name: str
    base_url: str | None = None
    api_key_env: str | None = None
    max_tokens: int = 8192
    num_ctx: int | None = None        # Ollama context window for this call (see context_for)

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
    if os.environ.get("SCA_OLLAMA_NUM_THREAD"):     # fewer CPU threads = cooler (and slower)
        kwargs["num_thread"] = int(os.environ["SCA_OLLAMA_NUM_THREAD"])
    if os.environ.get("SCA_OLLAMA_NUM_CTX"):
        kwargs["num_ctx"] = int(os.environ["SCA_OLLAMA_NUM_CTX"])
    elif spec.num_ctx:
        kwargs["num_ctx"] = spec.num_ctx
    return ChatOllama(**kwargs)


OLLAMA_CTX_SIZES = (4096, 8192, 16384, 32768, 65536, 131072)
REPLY_RESERVE = 4096   # tokens kept free for the answer


def context_for(prompt_chars: int) -> tuple[int, bool]:
    """Ollama silently cuts prompts longer than its context window (default 4096 tokens), so pick
    a window that fits prompt + answer. Sizes are rounded to a few fixed steps because every
    change makes Ollama reload the model. Returns (num_ctx, fits). The upper limit is
    SCA_OLLAMA_MAX_CTX (default 32768): bigger windows need much more (GPU) memory."""
    needed = prompt_chars // 3 + REPLY_RESERVE          # ~3 characters per token for code
    limit = int(os.environ.get("SCA_OLLAMA_MAX_CTX", "32768"))
    for size in OLLAMA_CTX_SIZES:
        if size >= needed and size <= limit:
            return size, True
    return max([s for s in OLLAMA_CTX_SIZES if s <= limit] or [4096]), False


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
        _check_key(key, required=True, example="sk-ant-...")
        make_model(spec, 0.0)
    elif spec.provider == "openai":
        key = spec.api_key_env or "OPENAI_API_KEY"
        # a local server (--base-url without --api-key-env) may need no key at all
        local = bool(spec.base_url or os.environ.get("OPENAI_BASE_URL")) and not spec.api_key_env
        _check_key(key, required=not local, example="...")
        make_model(spec, 0.0)


def _check_key(name: str, required: bool, example: str) -> None:
    value = os.environ.get(name)
    if value is None or value == "":
        if not required:
            return
        state = "is empty" if value == "" else "is not set"
        raise ModelError(f"{name} {state}. Set it with no spaces around '=':\n"
                         f"    export {name}={example}\n"
                         f"Check it with:  echo ${{{name}:0:8}}")
    if value != value.strip():
        raise ModelError(f"{name} starts or ends with a space. Set it again with no spaces around '=':\n"
                         f"    export {name}={example}")


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


def retry_after(text: str) -> float | None:
    """Seconds to wait, if the error says so ('Please try again in 12.5s', '... in 850ms', '1m30s')."""
    m = re.search(r"try again in\s+(?:(\d+)m(?!s))?\s*([\d.]+)?\s*(ms|s)?", text, re.IGNORECASE)
    if not m or not (m.group(1) or m.group(2)):
        return None
    minutes = float(m.group(1) or 0)
    value = float(m.group(2) or 0)
    seconds = value / 1000 if (m.group(3) or "").lower() == "ms" else value
    return minutes * 60 + seconds


def invoke_with_retry(model: BaseChatModel, messages, retries: int = 4, base_delay: float = 2.0,
                      max_wait: float = 90.0) -> str:
    """Call the model; retry temporary failures (rate limits, overload, network) with backoff,
    waiting as long as the provider asks for when it says so."""
    for attempt in range(retries + 1):
        try:
            return message_text(model.invoke(messages))
        except Exception as e:  # noqa: BLE001 - providers raise many error types
            text = f"{type(e).__name__}: {e}".lower()
            if attempt == retries or not any(k in text for k in _RETRYABLE):
                raise ModelError(f"model call failed: {e}") from e
            wait = retry_after(str(e))
            time.sleep(min(wait + 0.5 if wait is not None else base_delay * (2 ** attempt), max_wait))
    raise AssertionError("unreachable")
