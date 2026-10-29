import pytest

from safe_coding_agent.prompts import code_prompt, feedback_text, parse_files
from safe_coding_agent.sandbox import FailedTest, RunResult
from safe_coding_agent.tasks import TaskError, builtin_suite_dir, load_suite, load_task, unsafe_path_reason

from .conftest import ADD_TESTS


def test_load_task_defaults(make_task):
    t = load_task(make_task(ADD_TESTS))
    assert t.files == ["solution.py"] and t.level == "custom" and t.timeout == 60
    assert t.safety == "standard" and not t.show_tests and t.count_tests() == 3


def test_load_task_fields(make_task):
    t = load_task(make_task(ADD_TESTS, files="[pkg/a.py, pkg/b.py]", level="hard", timeout=5,
                            show_tests="true", safety="strict", allow_imports="[subprocess]"))
    assert t.files == ["pkg/a.py", "pkg/b.py"] and t.level == "hard" and t.timeout == 5
    assert t.show_tests and t.safety == "strict" and t.allow_imports == ["subprocess"]


def test_prompt_from_task_md(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_x(): pass\n")
    (tmp_path / "task.yaml").write_text("name: md\n")
    (tmp_path / "task.md").write_text("# Build it\nDo the thing.")
    assert "Do the thing." in load_task(tmp_path).prompt


@pytest.mark.parametrize("yaml_text, error", [
    ("name: x\n", "no prompt"),
    ("prompt: hi\nfiles: [../evil.py]\n", ".."),
    ("prompt: hi\nfiles: [tests/test_x.py]\n", "tests"),
    ("prompt: hi\nsafety: maybe\n", "safety"),
    ("prompt: hi\ntimeout: soon\n", "timeout"),
    ("- just\n- a list\n", "mapping"),
])
def test_bad_task_yaml(tmp_path, yaml_text, error):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_x(): pass\n")
    (tmp_path / "task.yaml").write_text(yaml_text)
    with pytest.raises(TaskError, match=error):
        load_task(tmp_path)


def test_missing_tests(tmp_path):
    (tmp_path / "task.yaml").write_text("prompt: hi\n")
    with pytest.raises(TaskError, match="tests"):
        load_task(tmp_path)


def test_builtin_suite_loads():
    tasks = load_suite(builtin_suite_dir())
    assert len(tasks) == 13
    assert {t.level for t in tasks} == {"easy", "medium", "hard", "tricky"}
    assert all(t.count_tests() > 0 for t in tasks)


@pytest.mark.parametrize("path, ok", [
    ("solution.py", True), ("pkg/mod.py", True), ("../x.py", False), ("/etc/passwd", False),
    ("tests/test_a.py", False), ("conftest.py", False), ("pkg/conftest.py", False),
    (".env", False), ("pkg/.hidden/x.py", False), ("C:/x.py", False), ("", False),
])
def test_unsafe_paths(path, ok):
    assert (unsafe_path_reason(path) is None) == ok


@pytest.mark.parametrize("text", [
    "FILE: solution.py\n```python\ndef add(a, b):\n    return a + b\n```",
    "**FILE: `solution.py`**\n```python\ndef add(a, b):\n    return a + b\n```",
    "### File: solution.py\n\n```py\ndef add(a, b):\n    return a + b\n```",
    "Here you go:\n```python\ndef add(a, b):\n    return a + b\n```\nDone.",
    "FILE: ./solution.py\n```python\ndef add(a, b):\n    return a + b\n```",
])
def test_parse_single_file_formats(make_task, text):
    files, problems = parse_files(text, load_task(make_task(ADD_TESTS)))
    assert problems == [] and files == {"solution.py": "def add(a, b):\n    return a + b"}


def test_parse_multiple_files(make_task):
    task = load_task(make_task(ADD_TESTS, files="[a.py, pkg/b.py]"))
    text = "FILE: a.py\n```python\nA = 1\n```\n\nFILE: pkg/b.py\n```python\nB = 2\n```"
    files, problems = parse_files(text, task)
    assert files == {"a.py": "A = 1", "pkg/b.py": "B = 2"} and problems == []


def test_parse_refuses_tests_and_escapes(make_task):
    task = load_task(make_task(ADD_TESTS))
    text = ("FILE: tests/test_task.py\n```python\ndef test_x(): pass\n```\n"
            "FILE: ../../evil.py\n```python\nx\n```\n"
            "FILE: ./.secret.py\n```python\nx\n```\n"
            "FILE: solution.py\n```python\nok = 1\n```")
    files, problems = parse_files(text, task)
    assert files == {"solution.py": "ok = 1"}
    assert len(problems) == 3


def test_parse_nothing(make_task):
    files, problems = parse_files("I cannot help with that.", load_task(make_task(ADD_TESTS)))
    assert files == {} and problems


def test_prompt_includes_starter_and_respects_budget(make_task):
    task = load_task(make_task(ADD_TESTS, starter={"lib/big.py": "x = 1\n" * 5000, "lib/small.py": "y = 2\n"},
                               show_tests="true"))
    p = code_prompt(task, {}, "", "", [], budget=2000)
    assert "lib/small.py" in p and "Not shown because of size: lib/big.py" in p
    p2 = code_prompt(task, {}, "", "", [], budget=1_000_000)
    assert "FILE: lib/big.py" in p2 and "Tests your code must pass" in p2


def test_feedback_modes():
    res = RunResult(passed=1, total=3, output="== FAILURES ==\nE   assert 2 == 3\n",
                    failures=[FailedTest("tests.test_a.test_x", "assert 2 == 3")])
    assert "1 of 3 tests passed" in feedback_text(res, "detailed")
    assert "assert 2 == 3" in feedback_text(res, "detailed")
    simple = feedback_text(res, "simple")
    assert "tests.test_a.test_x" in simple and "FAILURES" not in simple
    assert "timed out" in feedback_text(RunResult(timed_out=True), "detailed")
