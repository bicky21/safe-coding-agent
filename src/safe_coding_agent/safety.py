"""Static safety check for model-written code (AST based).

This is a first line of defence: it reads the code's structure and rejects things that a
solution to a normal coding task should not need - running shell commands, deleting
files, opening network connections, loading code dynamically, or reaching into Python
internals to get around these rules.

Two levels:
  standard (default) - blocks network, starting programs, deleting/moving files,
                       dynamic code (eval/exec/importlib) and sandbox-escape tricks
                       (__subclasses__, __globals__, frame objects, ...).
  strict             - also blocks writing files, sys/pathlib/inspect, computed
                       getattr(), os.environ and object internals like __dict__.
  off                - no static check (only the runner's isolation protects you).

It is NOT a sandbox. Determined code can always find a way around a static check, so the
real protection is running the tests in an isolated runner (see sandbox.py; use the
Docker runner for untrusted models).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

# Modules a solution may not import (top-level name). Tasks can allow some via allow_imports.
BLOCKED_MODULES = {
    "subprocess": "running programs",
    "socket": "network access",
    "ssl": "network access",
    "http": "network access",
    "urllib": "network access",
    "urllib3": "network access",
    "requests": "network access",
    "httpx": "network access",
    "aiohttp": "network access",
    "ftplib": "network access",
    "smtplib": "network access",
    "telnetlib": "network access",
    "paramiko": "network access",
    "shutil": "deleting or moving files",
    "ctypes": "calling C code directly",
    "cffi": "calling C code directly",
    "multiprocessing": "starting processes",
    "pty": "starting processes",
    "importlib": "loading code dynamically",
    "runpy": "running other code",
    "code": "running other code",
    "codeop": "running other code",
    "marshal": "loading compiled code",
    "pickle": "loading untrusted objects",
    "builtins": "changing Python built-ins",
    "signal": "changing process signals",
    "resource": "changing process limits",
    "webbrowser": "opening programs",
}
STRICT_ONLY_MODULES = {
    "gc": "reaching into Python internals",
    "inspect": "reaching into Python internals",
    "sys": "changing the interpreter",
    "pathlib": "file system access",
    "tempfile": "file system access",
    "glob": "file system access",
    "io": "file system access",
}

# Calls that are blocked no matter how the module was imported.
BLOCKED_CALLS = {
    "eval": "running hidden code",
    "exec": "running hidden code",
    "compile": "running hidden code",
    "__import__": "hidden imports",
    "breakpoint": "starting a debugger",
    "input": "waiting for keyboard input",
}
STRICT_ONLY_CALLS = {
    "globals": "reaching into Python internals",
    "vars": "reaching into Python internals",
    "locals": "reaching into Python internals",
    "delattr": "changing objects dynamically",
    "setattr": "changing objects dynamically",
}

# os.<name> calls that are blocked (os itself may be imported, e.g. for os.path.join).
BLOCKED_OS_ATTRS = {
    "system": "running shell commands", "popen": "running shell commands",
    "remove": "deleting files", "unlink": "deleting files", "rmdir": "deleting folders",
    "removedirs": "deleting folders", "rename": "moving files", "replace": "moving files",
    "kill": "killing processes", "killpg": "killing processes", "fork": "starting processes",
    "forkpty": "starting processes", "chown": "changing file owners",
    "symlink": "creating links", "link": "creating links", "truncate": "changing files",
}
STRICT_ONLY_OS_ATTRS = {
    "chmod": "changing file permissions", "putenv": "changing environment variables",
    "unsetenv": "changing environment variables", "environ": "reading environment variables",
    "getenv": "reading environment variables", "chdir": "changing directory",
}
BLOCKED_OS_PREFIXES = ("exec", "spawn", "posix_spawn")

# Attribute names that are typical sandbox-escape tricks.
BLOCKED_DUNDERS = {
    "__subclasses__", "__globals__", "__builtins__", "__code__", "__closure__",
    "__getattribute__", "__loader__", "__spec__", "__reduce__", "__reduce_ex__",
    "f_globals", "f_locals", "f_back", "f_builtins", "gi_frame", "cr_frame", "tb_frame",
}
STRICT_ONLY_DUNDERS = {"__dict__", "__class__", "__bases__", "__mro__", "__base__", "__self__", "__func__"}

LEVELS = ("standard", "strict", "off")

WRITE_MODES = set("wax+")


@dataclass
class Violation:
    file: str
    line: int
    reason: str
    code: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: {self.reason}: {self.code}"


class _Checker(ast.NodeVisitor):
    def __init__(self, filename: str, source: str, allowed: set[str], strict: bool):
        self.filename = filename
        self.lines = source.splitlines()
        self.allowed = allowed
        self.strict = strict
        self.modules = {**BLOCKED_MODULES, **(STRICT_ONLY_MODULES if strict else {})}
        self.calls = {**BLOCKED_CALLS, **(STRICT_ONLY_CALLS if strict else {})}
        self.os_attrs = {**BLOCKED_OS_ATTRS, **(STRICT_ONLY_OS_ATTRS if strict else {})}
        self.dunders = BLOCKED_DUNDERS | (STRICT_ONLY_DUNDERS if strict else set())
        self.os_names = {"os"}        # names that refer to the os module
        self.risky_names = {"os", "builtins", "__builtins__", "sys", "posix", "nt"}  # dangerous objects
        self.violations: list[Violation] = []

    def flag(self, node: ast.AST, reason: str) -> None:
        line = getattr(node, "lineno", 0)
        code = self.lines[line - 1].strip() if 0 < line <= len(self.lines) else ""
        self.violations.append(Violation(self.filename, line, reason, code[:120]))

    def _module_blocked(self, name: str) -> str | None:
        top = name.split(".")[0]
        if top in self.allowed or name in self.allowed:
            return None
        return self.modules.get(top)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            reason = self._module_blocked(alias.name)
            if reason:
                self.flag(node, f"import of '{alias.name}' ({reason})")
            if alias.name == "os":
                self.os_names.add(alias.asname or "os")
            if alias.name.split(".")[0] in BLOCKED_MODULES or alias.name in self.risky_names:
                self.risky_names.add(alias.asname or alias.name.split(".")[0])
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        reason = self._module_blocked(mod) if mod else None
        if reason:
            self.flag(node, f"import from '{mod}' ({reason})")
        if mod == "os" and "os" not in self.allowed:
            for alias in node.names:
                r = self._os_reason(alias.name)
                if r or alias.name == "*":
                    self.flag(node, f"'from os import {alias.name}' ({r or 'importing everything from os'})")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Name) and func.id in self.calls and func.id not in self.allowed:
            self.flag(node, f"call to {func.id}() ({self.calls[func.id]})")
        if isinstance(func, ast.Name) and func.id == "getattr" and "getattr" not in self.allowed:
            # getattr(obj, "literal") is fine unless the literal itself is blocked;
            # getattr(obj, <computed string>) can reach anything (strict mode blocks it).
            if len(node.args) >= 2:
                attr = node.args[1]
                target = node.args[0]
                on_risky = isinstance(target, ast.Name) and target.id in self.risky_names
                if not (isinstance(attr, ast.Constant) and isinstance(attr.value, str)):
                    if self.strict or on_risky:
                        self.flag(node, "getattr() with a computed name (can bypass safety rules)")
                elif attr.value in self.dunders or attr.value in self.os_attrs \
                        or attr.value.startswith(BLOCKED_OS_PREFIXES):
                    self.flag(node, f"getattr() of '{attr.value}'")
        if self.strict and isinstance(func, ast.Name) and func.id == "open" and "open" not in self.allowed:
            mode = _open_mode(node)
            if mode is None:
                self.flag(node, "open() with a computed mode (may write files)")
            elif set(mode) & WRITE_MODES:
                self.flag(node, f"open() for writing (mode '{mode}')")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in self.dunders:
            self.flag(node, f"access to '{node.attr}' (reaching into Python internals)")
        if isinstance(node.value, ast.Name) and node.value.id in self.os_names and "os" not in self.allowed:
            reason = self._os_reason(node.attr)
            if reason:
                self.flag(node, f"os.{node.attr} ({reason})")
        if node.attr in {"unlink", "rmdir", "rmtree"} or (
                self.strict and node.attr in {"write_text", "write_bytes"}):
            self.flag(node, f".{node.attr}() (changing files)")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in {"__builtins__", "__loader__", "__spec__"}:
            self.flag(node, f"use of '{node.id}' (reaching into Python internals)")
        self.generic_visit(node)


    def _os_reason(self, name: str) -> str | None:
        if name in self.os_attrs:
            return self.os_attrs[name]
        if name.startswith(BLOCKED_OS_PREFIXES):
            return "running programs"
        return None


def _open_mode(node: ast.Call) -> str | None:
    """The mode passed to open(), '' for the default ('r'), or None if not a literal."""
    mode_node = node.args[1] if len(node.args) >= 2 else None
    for kw in node.keywords:
        if kw.arg == "mode":
            mode_node = kw.value
    if mode_node is None:
        return "r"
    if isinstance(mode_node, ast.Constant) and isinstance(mode_node.value, str):
        return mode_node.value
    return None


def check_source(source: str, filename: str = "solution.py",
                 allow: list[str] | set[str] | None = None, level: str = "standard") -> list[Violation]:
    """Return every safety violation in one Python file (empty list = looks safe)."""
    if level not in LEVELS:
        raise ValueError(f"safety level must be one of {LEVELS}, not {level!r}")
    if level == "off":
        return []
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return []  # not runnable anyway; the test run will report the syntax error
    checker = _Checker(filename, source, set(allow or []), strict=(level == "strict"))
    checker.visit(tree)
    return checker.violations


def check_files(files: dict[str, str], allow: list[str] | None = None,
                level: str = "standard") -> list[Violation]:
    """Check every .py file the model wrote."""
    out: list[Violation] = []
    for name, text in files.items():
        if name.endswith(".py"):
            out.extend(check_source(text, name, allow, level))
    return out
