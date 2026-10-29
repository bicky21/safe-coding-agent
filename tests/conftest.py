"""Shared test helpers: a scripted fake model and a small task factory."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from safe_coding_agent.models import parse_model, register_provider


class Script:
    """Replies the fake model gives, in order, plus a record of every call."""

    def __init__(self) -> None:
        self.replies: list[str] = []
        self.calls: list[dict[str, Any]] = []

    def next_reply(self, prompt: str, temperature: float) -> str:
        self.calls.append({"prompt": prompt, "temperature": temperature})
        if not self.replies:
            raise AssertionError("the fake model ran out of scripted replies")
        return self.replies.pop(0)


SCRIPT = Script()


class ScriptedModel(BaseChatModel):
    temperature: float = 0.0

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        prompt = messages[-1].content
        text = SCRIPT.next_reply(prompt, self.temperature)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])


register_provider("scripted", lambda spec, temperature: ScriptedModel(temperature=temperature))


@pytest.fixture
def script():
    SCRIPT.replies.clear()
    SCRIPT.calls.clear()
    yield SCRIPT
    SCRIPT.replies.clear()
    SCRIPT.calls.clear()


@pytest.fixture
def model_spec():
    return parse_model("scripted:test")


def reply(files: dict[str, str]) -> str:
    """A well-formed model reply containing these files."""
    return "\n\n".join(f"FILE: {path}\n```python\n{code}\n```" for path, code in files.items())


@pytest.fixture
def make_task(tmp_path):
    """make_task(tests="...", **yaml_fields) -> path of a new task folder."""
    counter = {"n": 0}

    def _make(tests: str, prompt: str = "Write add(a, b) in solution.py.", starter: dict | None = None,
              **fields) -> Path:
        counter["n"] += 1
        folder = tmp_path / f"task{counter['n']}"
        (folder / "tests").mkdir(parents=True)
        lines = [f"name: task{counter['n']}", "prompt: |", textwrap.indent(prompt, "  ")]
        for k, v in fields.items():
            lines.append(f"{k}: {v}")
        (folder / "task.yaml").write_text("\n".join(lines) + "\n")
        (folder / "tests" / "test_task.py").write_text(textwrap.dedent(tests))
        for rel, text in (starter or {}).items():
            p = folder / "starter" / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        return folder

    return _make


ADD_TESTS = """
import pytest
from solution import add

@pytest.mark.parametrize("a, b, c", [(1, 2, 3), (0, 0, 0), (-1, 1, 0)])
def test_add(a, b, c):
    assert add(a, b) == c
"""
