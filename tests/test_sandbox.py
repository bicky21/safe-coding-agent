import os
from pathlib import Path

import pytest

from safe_coding_agent.sandbox import DockerRunner, LocalRunner, build_workspace, get_runner, summarize_output
from safe_coding_agent.tasks import load_task

from .conftest import ADD_TESTS


@pytest.fixture
def add_task(make_task):
    return load_task(make_task(ADD_TESTS, timeout=5))


def test_all_pass(add_task):
    r = LocalRunner().run(add_task, {"solution.py": "def add(a, b):\n    return a + b\n"})
    assert (r.passed, r.total, r.all_passed) == (3, 3, True)


def test_partial_credit(add_task):
    r = LocalRunner().run(add_task, {"solution.py": "def add(a, b):\n    return a * b + (a == b == 0)*0\n"})
    assert r.total == 3 and 0 < r.passed < 3 and not r.all_passed
    assert r.failures and "assert" in r.output


def test_import_error_scores_zero_of_all(add_task):
    r = LocalRunner().run(add_task, {"solution.py": "def add(a, b) return"})
    assert (r.passed, r.total, r.collection_error) == (0, 3, True)


def test_timeout_is_killed(add_task):
    r = LocalRunner().run(add_task, {"solution.py": "def add(a, b):\n    while True:\n        pass\n"},
                          timeout=2)
    assert r.timed_out and r.passed == 0 and r.total == 3 and "TIMEOUT" in r.output


def test_environment_is_scrubbed(make_task, monkeypatch):
    monkeypatch.setenv("MY_SECRET_API_KEY", "sk-should-not-leak")
    task = load_task(make_task("""
        import os
        def test_no_secret():
            assert "MY_SECRET_API_KEY" not in os.environ
    """))
    assert LocalRunner().run(task, {"solution.py": "x = 1"}).all_passed


def test_model_cannot_replace_tests(add_task, tmp_path):
    ws = build_workspace(add_task, {"solution.py": "x = 1", "tests/test_task.py": "def test_x(): pass"},
                         tmp_path)
    assert "from solution import add" in (ws / "tests" / "test_task.py").read_text()


def test_workspace_refuses_escape(add_task, tmp_path):
    with pytest.raises(ValueError):
        build_workspace(add_task, {"../outside.py": "x = 1"}, tmp_path)


def test_starter_files_and_multi_file(make_task):
    task = load_task(make_task("""
        from pkg.core import double
        from pkg.extra import triple
        def test_double():
            assert double(2) == 4
        def test_triple():
            assert triple(2) == 6
    """, starter={"pkg/__init__.py": "", "pkg/core.py": "def double(x):\n    return 2 * x\n"}))
    r = LocalRunner().run(task, {"pkg/extra.py": "def triple(x):\n    return 3 * x\n"})
    assert r.all_passed


def test_one_broken_test_file_does_not_hide_the_others(make_task, tmp_path):
    folder = make_task("""
        from solution import a
        def test_a():
            assert a() == 1
    """)
    (folder / "tests" / "test_other.py").write_text(
        "from missing_module import b\n\ndef test_b():\n    assert b() == 2\n\ndef test_b2():\n    assert b()\n")
    r = LocalRunner().run(load_task(folder), {"solution.py": "def a():\n    return 1\n"})
    assert (r.passed, r.total) == (1, 3) and not r.collection_error


def test_docker_command_is_locked_down(tmp_path):
    cmd = " ".join(DockerRunner(image="img").command(Path("/ws"), "c1"))
    for flag in ("--network none", "--read-only", "--cap-drop ALL", "no-new-privileges",
                 "--pids-limit", "--memory", "--rm"):
        assert flag in cmd
    assert "--user 0:" not in cmd, "the container must never run as root"
    if hasattr(os, "getuid") and os.getuid() != 0:
        assert f"--user {os.getuid()}:{os.getgid()}" in cmd


def test_auto_runner_falls_back_to_local_with_warning(monkeypatch):
    monkeypatch.setattr("safe_coding_agent.sandbox.docker_status", lambda image: (False, "no docker"))
    runner, note = get_runner("auto")
    assert runner.name == "local" and "LOCAL" in note


def test_full_assertion_diff_is_shown(make_task):
    task = load_task(make_task("""
        from solution import order
        def test_order():
            assert order() == ["write report", "buy milk", "call mom", "walk dog", "pay bills"]
    """))
    r = LocalRunner().run(task, {"solution.py": "def order():\n    return ['buy milk', 'call mom', "
                                                "'walk dog', 'pay bills', 'write report']\n"})
    assert "['buy milk', 'call mom', 'walk dog', 'pay bills', 'write report']" in r.output
    assert "generated xml file" not in summarize_output(r.output)
