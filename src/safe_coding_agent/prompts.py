"""Prompts sent to the model, and parsing the files out of its reply."""

from __future__ import annotations

import ast
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


_GAVE_UP = re.compile(r"\b(sorry|can['’]?t|cannot|unable|not able|too (?:complex|long|big)|beyond the scope)\b",
                      re.IGNORECASE)

GIVE_IT_A_GO = ("You did not write any code. This task IS doable: a complete solution is usually 100-300 lines, "
                "and it does not have to be perfect - you will get the test results and can fix it after. "
                "Write your best complete version now.")


def gave_up(reply: str) -> bool:
    """A short reply without any code that declines the task ("I'm sorry, but I can't...")."""
    return "```" not in reply and len(reply) < 2000 and bool(_GAVE_UP.search(reply))


def first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip() and not line.startswith("="):
            return line.strip()[:200]
    return text.strip()[:200]


# ---------------------------------------------------------------- parsing replies
#
# Models name their files in many ways. All of these are understood:
#
#   FILE: todo/store.py            **todo/store.py**             ### `todo/store.py`
#   ```python                      ```python                     ```python
#
#   ```python todo/store.py        ```python:todo/store.py       ```python title="todo/store.py"
#
#   ```python
#   # todo/store.py                (or "# File: todo/store.py" as the first line in the block)

_FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})([^\n]*)\n(.*?)\n[ \t]*\1[ \t]*$", re.MULTILINE | re.DOTALL)
_PATH = r"[A-Za-z0-9_./][A-Za-z0-9_./-]*\.[A-Za-z0-9]+"   # leading ./ or ../ allowed: refused later
_LABEL_LINE = re.compile(
    r"^[ \t>*#_\-\d.)]*(?:(?:file(?:name)?|path)\s*[:=]\s*)?[*_`\"']*(" + _PATH + r")[*_`\"']*[ \t]*:?[ \t*_]*$",
    re.IGNORECASE)
_INFO_PATH = re.compile(r"(?:title\s*=\s*[\"']?|:|\s)(" + _PATH + r")[\"']?\s*$")
_COMMENT_PATH = re.compile(r"^\s*(?:#|//)\s*(?:(?:file(?:name)?|path)\s*[:=]\s*)?(" + _PATH + r")\s*$",
                           re.IGNORECASE)
_CODE_LANGS = {"", "python", "py", "python3"}


def _path_before(text: str, start: int, known: set[str]) -> str | None:
    """A file name on the last non-empty line just before a code block: either the whole line
    ("**todo/store.py**") or, inside a sentence ("Updated `todo/store.py`:"), a known project file."""
    lines = text[:start].rstrip("\n").split("\n")
    for line in reversed(lines[-3:]):
        if not line.strip():
            continue
        m = _LABEL_LINE.match(line)
        if m:
            return m.group(1)
        mentioned = {p.strip("./") if p.startswith("./") else p for p in re.findall(_PATH, line)}
        hits = [p for p in mentioned if p in known]
        return hits[0] if len(hits) == 1 else None
    return None


def _top_level_names(code: str) -> set[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set(re.findall(r"^(?:def|class)\s+(\w+)", code, re.MULTILINE))
    return {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def _match_unnamed(blocks: list[str], task: Task) -> dict[str, str]:
    """Several code blocks without names, one per expected file: match them by content
    (a block defining TodoStore belongs to the file that already defines TodoStore, or whose
    tests import it). Returns {} when the match is not clear."""
    if len(blocks) != len(task.files) or len(blocks) < 2:
        return {}
    starter = task.starter_files()
    tests = "\n".join(task.test_files().values())
    expected: dict[str, set[str]] = {}
    for f in task.files:
        names = _top_level_names(starter.get(f, ""))
        module = f[:-3].replace("/", ".") if f.endswith(".py") else f
        for m in re.finditer(r"from\s+" + re.escape(module) + r"\s+import\s+([\w, ]+)", tests):
            names |= {n.strip() for n in m.group(1).split(",") if n.strip()}
        expected[f] = names
    result: dict[str, str] = {}
    for body in blocks:
        names = _top_level_names(body)
        scores = sorted(((len(names & want), f) for f, want in expected.items() if f not in result), reverse=True)
        if not scores or scores[0][0] == 0 or (len(scores) > 1 and scores[0][0] == scores[1][0]):
            return {}
        result[scores[0][1]] = body
    return result


def parse_files(reply: str, task: Task) -> tuple[dict[str, str], list[str]]:
    """Returns ({path: content}, problems). Paths into tests/ or outside the project are refused."""
    files: dict[str, str] = {}
    problems: list[str] = []
    unnamed: list[tuple[str, str]] = []
    known = set(task.files) | set(task.starter_files())
    for m in _FENCE.finditer(reply):
        info, body = m.group(2).strip(), m.group(3)
        lang = info.split()[0].split(":")[0].lower() if info else ""
        path = None
        im = _INFO_PATH.search(info) if info else None
        if im:
            path = im.group(1)
        elif "." in lang and re.fullmatch(_PATH, lang):        # ```todo/store.py
            path, lang = lang, lang.rsplit(".", 1)[-1]
        if not path:
            path = _path_before(reply, m.start(), known)
        if not path:
            first = body.split("\n", 1)[0]
            cm = _COMMENT_PATH.match(first)
            if cm:
                path = cm.group(1)
        if not path:
            unnamed.append((lang, body))
            continue
        path = path.strip().removeprefix("./")
        reason = unsafe_path_reason(path)
        if reason:
            problems.append(f"{path}: {reason}")
            continue
        files[path] = body

    code = [body for lang, body in unnamed if lang in _CODE_LANGS]
    if not files and len(task.files) == 1 and code:
        # no file names at all: accept the longest code block as the one expected file
        files[task.files[0]] = max(code, key=len)
    elif not files and code:
        files.update(_match_unnamed(code, task))
    if not files and not problems:
        if unnamed:
            problems.append(f"found {len(unnamed)} code block(s) but no file names - put "
                            "'FILE: path/to/file.py' on the line above each block")
        else:
            problems.append("no files found in your answer")
    return files, problems
