import pytest

from safe_coding_agent.safety import check_files, check_source

BLOCKED_IN_STANDARD = {
    "os.system": "import os\nos.system('rm -rf /')",
    "os alias": "import os as o\no.system('ls')",
    "from os import system": "from os import system\nsystem('ls')",
    "os.remove": "import os\nos.remove('x')",
    "os.exec*": "import os\nos.execv('/bin/sh', ['sh'])",
    "subprocess": "import subprocess\nsubprocess.run(['ls'])",
    "from subprocess": "from subprocess import run",
    "socket": "import socket",
    "urllib.request": "import urllib.request",
    "requests": "import requests",
    "shutil": "import shutil\nshutil.rmtree('/')",
    "ctypes": "import ctypes",
    "importlib": "import importlib\nimportlib.import_module('os')",
    "eval": "eval('1+1')",
    "exec": "exec('x=1')",
    "__import__": "__import__('os').system('ls')",
    "computed getattr on os": "import os\ngetattr(os, 'sys' + 'tem')('ls')",
    "computed getattr on builtins": "import builtins\ngetattr(builtins, 'ev' + 'al')('1')",
    "literal getattr os.system": "import os\ngetattr(os, 'system')('ls')",
    "subclasses escape": "x = ().__class__.__bases__[0].__subclasses__()",
    "globals via function": "def f(): pass\nf.__globals__['os']",
    "frame escape": "import sys\nf = sys._getframe().f_globals",
    "__builtins__": "__builtins__['eval']('1')",
    "pathlib unlink": "from pathlib import Path\nPath('x').unlink()",
    "input": "name = input()",
}


@pytest.mark.parametrize("code", BLOCKED_IN_STANDARD.values(), ids=BLOCKED_IN_STANDARD.keys())
def test_standard_blocks(code):
    assert check_source(code), f"should be blocked:\n{code}"


ALLOWED_IN_STANDARD = {
    "os.path": "import os\np = os.path.join('a', 'b')\nos.path.exists(p)",
    "stdlib": "import re, math, json, collections, itertools, functools, heapq, dataclasses",
    "typing": "from typing import Optional\nfrom dataclasses import dataclass, field",
    "class internals": "class A:\n    def name(self):\n        return self.__class__.__name__, vars",
    "dict": "class A: pass\nA().__dict__",
    "own getattr": "class A: x = 1\ngetattr(A(), field_name, None)",
    "read file": "open('data.txt').read()",
    "write file": "open('out.txt', 'w').write('x')",
    "sys": "import sys\nsys.maxsize",
    "pathlib read": "from pathlib import Path\nPath('x').read_text()",
    "calendar": "import calendar, datetime",
}


@pytest.mark.parametrize("code", ALLOWED_IN_STANDARD.values(), ids=ALLOWED_IN_STANDARD.keys())
def test_standard_allows_normal_code(code):
    assert check_source(code) == []


@pytest.mark.parametrize("code", [
    "open('out.txt', 'w')",
    "import sys",
    "class A: pass\ngetattr(A(), name)",
    "class A: pass\nA().__dict__",
    "import os\nos.environ['X']",
    "open('f', mode)",
])
def test_strict_blocks_more(code):
    assert check_source(code) == [] or "import os" in code
    assert check_source(code, level="strict")


def test_off_allows_everything():
    assert check_source("import os\nos.system('ls')", level="off") == []


def test_allow_list():
    code = "import subprocess\nsubprocess.run(['git', 'status'])"
    assert check_source(code)
    assert check_source(code, allow=["subprocess"]) == []


def test_syntax_error_is_not_a_violation():
    assert check_source("def broken(:") == []


def test_violation_has_location():
    [v] = check_source("x = 1\nimport socket\n", "pkg/mod.py")
    assert v.file == "pkg/mod.py" and v.line == 2 and "socket" in v.reason
    assert str(v).startswith("pkg/mod.py:2:")


def test_check_files_only_python():
    files = {"notes.md": "import os; os.system('x')", "a.py": "import socket"}
    found = check_files(files)
    assert [v.file for v in found] == ["a.py"]


def test_bad_level():
    with pytest.raises(ValueError):
        check_source("x = 1", level="paranoid")
