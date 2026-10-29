"""Task format and loading.

A task is a folder:

    my-task/
      task.yaml        required: name, prompt (or put the prompt in task.md)
      task.md          optional: the prompt as Markdown (used when task.yaml has no prompt)
      tests/           required: pytest tests that decide if the code is correct
      starter/         optional: existing code the model builds on (copied into the workspace)

task.yaml fields:

    name: my-task                # defaults to the folder name
    prompt: |                    # what the model must build
      Write a function ...
    files: [solution.py]         # files the model is expected to write (shown in the prompt)
    level: custom                # any tag, used to filter: sca bench --level tricky
    timeout: 60                  # seconds allowed for one test run
    show_tests: false            # true = the model sees the test files in its prompt
    allow_imports: []            # modules the safety check should allow (e.g. [subprocess])
    safety: standard             # standard | strict | off (see safety.py)
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PROTECTED_NAMES = {"conftest.py", "pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml",
                   "_sca_timeout.py"}   # the runner's own per-test time-limit plugin


class TaskError(ValueError):
    """A task folder is missing something or has an invalid field."""


@dataclass
class Task:
    name: str
    prompt: str
    path: Path
    files: list[str] = field(default_factory=lambda: ["solution.py"])
    level: str = "custom"
    timeout: int = 60
    show_tests: bool = False
    allow_imports: list[str] = field(default_factory=list)
    safety: str = "standard"

    @property
    def tests_dir(self) -> Path:
        return self.path / "tests"

    @property
    def starter_dir(self) -> Path:
        return self.path / "starter"

    def starter_files(self) -> dict[str, str]:
        return read_tree(self.starter_dir)

    def test_files(self) -> dict[str, str]:
        return {f"tests/{k}": v for k, v in read_tree(self.tests_dir).items()}

    def count_tests(self) -> int:
        """Best-effort number of tests, used when pytest cannot even collect them
        (for example when the model's code has a syntax error)."""
        total = 0
        for name, text in self.test_files().items():
            if not name.endswith(".py"):
                continue
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            total += _count_tests_in_module(tree)
        return total


def _count_tests_in_module(tree: ast.Module) -> int:
    total = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            cases = 1
            for dec in node.decorator_list:
                # @pytest.mark.parametrize("a,b", [ ... ])  -> one test per list item
                if (isinstance(dec, ast.Call) and getattr(dec.func, "attr", "") == "parametrize"
                        and len(dec.args) >= 2 and isinstance(dec.args[1], (ast.List, ast.Tuple))):
                    cases *= max(len(dec.args[1].elts), 1)
            total += cases
    return total


def read_tree(root: str | os.PathLike) -> dict[str, str]:
    """All text files under root, as {relative/path: content}. Missing root -> {}."""
    root = Path(root)
    out: dict[str, str] = {}
    if not root.is_dir():
        return out
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        try:
            out[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # binary file: copied into the workspace, but not shown to the model
    return out


def load_task(folder: str | os.PathLike) -> Task:
    path = Path(folder).resolve()
    config_file = path / "task.yaml"
    if not config_file.is_file():
        raise TaskError(f"{path}: no task.yaml found")
    try:
        data = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise TaskError(f"{config_file}: invalid YAML: {e}") from e
    if not isinstance(data, dict):
        raise TaskError(f"{config_file}: must be a mapping of fields")

    prompt = data.get("prompt")
    if not prompt and (path / "task.md").is_file():
        prompt = (path / "task.md").read_text(encoding="utf-8")
    if not prompt or not str(prompt).strip():
        raise TaskError(f"{path}: no prompt (add 'prompt:' to task.yaml or a task.md file)")
    if not (path / "tests").is_dir() or not any((path / "tests").rglob("test*.py")):
        raise TaskError(f"{path}: no tests/test*.py files found")

    files = data.get("files", ["solution.py"])
    if isinstance(files, str):
        files = [files]
    for f in files:
        problem = unsafe_path_reason(f)
        if problem:
            raise TaskError(f"{config_file}: files: {f!r} {problem}")

    try:
        timeout = int(data.get("timeout", 60))
    except (TypeError, ValueError) as e:
        raise TaskError(f"{config_file}: timeout must be a number of seconds") from e

    safety = str(data.get("safety", "standard"))
    if safety not in ("standard", "strict", "off"):
        raise TaskError(f"{config_file}: safety must be standard, strict or off")

    return Task(
        name=str(data.get("name") or path.name),
        prompt=str(prompt).strip(),
        path=path,
        files=[str(f) for f in files],
        level=str(data.get("level", "custom")),
        timeout=max(timeout, 1),
        show_tests=bool(data.get("show_tests", False)),
        allow_imports=[str(m) for m in data.get("allow_imports", []) or []],
        safety=safety,
    )


def load_suite(folder: str | os.PathLike) -> list[Task]:
    """A folder of task folders (or a single task folder)."""
    path = Path(folder)
    if not path.is_dir():
        raise TaskError(f"{folder}: no such folder (built-in suites: {', '.join(BUILTIN_SUITES)})")
    if (path / "task.yaml").is_file():
        return [load_task(path)]
    tasks = [load_task(p) for p in sorted(path.iterdir()) if (p / "task.yaml").is_file()]
    if not tasks:
        raise TaskError(f"{path}: no task folders found (each needs a task.yaml)")
    return tasks


BUILTIN_SUITES = {
    "builtin": "benchmark",        # 13 short single-function tasks (easy ... tricky)
    "hard": "benchmark_hard",      # 5 project-style tasks: long exact specs, several files, existing code
}


def builtin_suite_dir(name: str = "builtin") -> Path:
    if name not in BUILTIN_SUITES:
        raise TaskError(f"unknown built-in suite {name!r}; choose one of: {', '.join(BUILTIN_SUITES)}")
    return Path(__file__).parent / BUILTIN_SUITES[name]


def resolve_suite(suite: str | None) -> tuple[Path, str]:
    """A built-in suite name ('builtin', 'hard') or a folder. Returns (folder, label)."""
    if not suite or suite in BUILTIN_SUITES:
        name = suite or "builtin"
        return builtin_suite_dir(name), name
    path = Path(suite)
    return path, str(path.resolve())


def unsafe_path_reason(rel: str) -> str | None:
    """Why the model may not write to this path, or None if it is fine."""
    p = Path(rel)
    if not rel or rel.strip() != rel:
        return "is empty or has surrounding spaces"
    if p.is_absolute() or rel.startswith(("/", "\\")) or (len(rel) > 1 and rel[1] == ":"):
        return "must be a relative path"
    if ".." in p.parts:
        return "must not contain '..'"
    if p.parts and p.parts[0] == "tests":
        return "is inside tests/ (tests can't be changed)"
    if p.name in PROTECTED_NAMES:
        return "is a test/config file that can't be changed"
    if any(part.startswith(".") for part in p.parts):
        return "must not be a hidden file or folder"
    return None
