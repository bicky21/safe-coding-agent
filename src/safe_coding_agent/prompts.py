"""Prompts sent to the model, and parsing the files out of its reply."""

from __future__ import annotations

import re

from .sandbox import RunResult, summarize_output
from .tasks import Task, unsafe_path_reason

SYSTEM = (
    "You are a careful senior Python developer. You write complete, working code that follows "
    "every rule in the task exactly. You never write or change tests."
)

OUTPUT_FORMAT = """Return every file you create or change in exactly this format,
with the FULL file content (no "..." placeholders):

FILE: path/to/file.py
```python
<full content of the file>
```

Do not change anything in tests/. Do not use input(), the network, or shell commands."""

PLAN_SYSTEM = "You are a careful senior Python developer. You plan before you code."


def _lang(path: str) -> str:
    return {"py": "python", "md": "markdown", "json": "json", "yaml": "yaml", "yml": "yaml",
            "toml": "toml", "js": "javascript", "ts": "typescript", "sh": "bash"}.get(
        path.rsplit(".", 1)[-1], "")


def render_files(files: dict[str, str], budget: int) -> tuple[str, int]:
    """Files as FILE blocks until the character budget runs out; the rest are listed by name."""
    parts, used, skipped = [], 0, []
    for path, text in files.items():
        block = f"FILE: {path}\n```{_lang(path)}\n{text}\n```\n"
        if used + len(block) > budget:
            skipped.append(path)
            continue
        parts.append(block)
        used += len(block)
    if skipped:
        parts.append("(Not shown because of size: " + ", ".join(skipped) + ")\n")
    return "\n".join(parts), used


def context_section(task: Task, current: dict[str, str], budget: int) -> str:
    """The code the model works on: starter files with the model's latest versions on top,
    plus the tests when the task shows them."""
    project = {**task.starter_files(), **current}
    out = []
    if project:
        text, used = render_files(project, budget)
        budget -= used
        out.append("Current project files:\n\n" + text)
    if task.show_tests:
        text, _ = render_files(task.test_files(), max(budget, 0))
        out.append("Tests your code must pass (read-only):\n\n" + text)
    return "\n".join(out)


def plan_prompt(task: Task, current: dict[str, str], plan: str, feedback: str, budget: int) -> str:
    p = [f"Task:\n{task.prompt}\n", f"Files to write: {', '.join(task.files)}\n"]
    ctx = context_section(task, current, budget)
    if ctx:
        p.append(ctx)
    p.append("Do NOT write code yet. Write a short, exact plan with three sections:\n"
             "RULES: every rule in the task as a numbered list, keeping every exact detail "
             "(order, direction, edge cases, when to raise errors).\n"
             "EXAMPLES: work through 3 small inputs by hand, step by step (input -> output), "
             "including an edge case. Check each result against the RULES.\n"
             "STEPS: the algorithm / design as numbered steps that follow the RULES.")
    if feedback:
        p.append(f"\nYour previous plan:\n{plan}\n\nCode written from it failed:\n{feedback}\n\n"
                 "Use the failing case as a worked example: go through that exact input by hand with "
                 "your RULES, find which rule or step is wrong or missing, and write a corrected plan. "
                 "If the approach itself is wrong, choose a different approach.")
    return "\n".join(p)


def code_prompt(task: Task, current: dict[str, str], plan: str, feedback: str,
                earlier: list[str], budget: int) -> str:
    p = [f"Task:\n{task.prompt}\n", f"Files to write: {', '.join(task.files)}\n"]
    ctx = context_section(task, current, budget)
    if ctx:
        p.append(ctx)
    if plan:
        p.append(f"Follow this plan exactly:\n{plan}\n")
    if earlier:
        p.append("Earlier attempts also failed:\n" + "\n".join(f"- {e}" for e in earlier) + "\n")
    if feedback:
        p.append(f"Your previous attempt failed:\n{feedback}\n\n"
                 "Re-read the task rules, find the real cause of the failure, and fix it. "
                 "Return the full content of every file you change.\n")
    p.append(OUTPUT_FORMAT)
    return "\n".join(p)


def feedback_text(res: RunResult, mode: str) -> str:
    if res.timed_out:
        return "The tests timed out (infinite loop or far too slow).\n" + summarize_output(res.output, 2000)
    head = f"{res.passed} of {res.total} tests passed."
    if res.collection_error:
        head = "The tests could not even run: importing your code failed."
    if mode == "simple":
        names = [f"- {f.name}: {f.message.splitlines()[0][:150] if f.message else 'failed'}"
                 for f in res.failures[:15]]
        return head + "\n" + "\n".join(names)
    return head + "\n" + summarize_output(res.output)


def first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip() and not line.startswith("="):
            return line.strip()[:200]
    return text.strip()[:200]


# ---------------------------------------------------------------- parsing replies

_FILE_BLOCK = re.compile(
    r"(?:^|\n)[ \t]*(?:[#>*_ ]*)(?:file|path)\s*[:=]\s*[*_`\"']*([^\s*`\"']+)[*_`\"']*[ \t]*\n+"
    r"[ \t]*```[^\n]*\n(.*?)\n[ \t]*```",
    re.IGNORECASE | re.DOTALL,
)
_ANY_BLOCK = re.compile(r"```([^\n]*)\n(.*?)\n```", re.DOTALL)


def parse_files(reply: str, task: Task) -> tuple[dict[str, str], list[str]]:
    """Returns ({path: content}, problems). Paths into tests/ or outside the project are refused."""
    files: dict[str, str] = {}
    problems: list[str] = []
    for path, body in _FILE_BLOCK.findall(reply):
        path = path.strip().removeprefix("./")
        reason = unsafe_path_reason(path)
        if reason:
            problems.append(f"{path}: {reason}")
            continue
        files[path] = body
    if not files and not problems and len(task.files) == 1:
        # no FILE markers: accept a single code block as the one expected file
        blocks = [(lang.strip().lower(), body) for lang, body in _ANY_BLOCK.findall(reply)]
        python = [b for lang, b in blocks if lang in ("python", "py", "")]
        if python:
            files[task.files[0]] = max(python, key=len)
    if not files and not problems:
        problems.append("no files found in your answer")
    return files, problems
