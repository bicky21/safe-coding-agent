from safe_coding_agent.agent import CodingAgent, Settings
from safe_coding_agent.sandbox import LocalRunner
from safe_coding_agent.tasks import load_task

from .conftest import ADD_TESTS, reply

GOOD = {"solution.py": "def add(a, b):\n    return a + b\n"}
BAD = {"solution.py": "def add(a, b):\n    return a - b\n"}


def run(task_path, spec, **settings):
    agent = CodingAgent(load_task(task_path), Settings(model=spec, **settings), LocalRunner())
    return agent.run()


def test_passes_first_try(make_task, script, model_spec):
    script.replies = [reply(GOOD)]
    r = run(make_task(ADD_TESTS), model_spec)
    assert r.status == "passed" and len(r.attempts) == 1
    assert (r.first_passed, r.best_passed, r.total) == (3, 3, 3)
    assert r.best_files == GOOD


def test_fixes_itself_using_feedback(make_task, script, model_spec):
    script.replies = [reply(BAD), reply(GOOD)]
    r = run(make_task(ADD_TESTS), model_spec)
    assert r.status == "passed" and [a.status for a in r.attempts] == ["failed", "passed"]
    assert r.first_passed == 1 and r.best_passed == 3
    second_prompt = script.calls[1]["prompt"]
    assert "Your previous attempt failed" in second_prompt and "add(" in second_prompt


def test_gives_up_after_max_attempts(make_task, script, model_spec):
    script.replies = [reply(BAD), reply({"solution.py": "def add(a, b):\n    return 0\n"})]
    r = run(make_task(ADD_TESTS), model_spec, max_attempts=2)
    assert r.status == "failed" and len(r.attempts) == 2
    assert (r.first_passed, r.best_passed) == (1, 2)  # "return 0" passes 0+0 and -1+1


def test_repeat_is_caught_without_running_tests(make_task, script, model_spec):
    script.replies = [reply(BAD), reply(BAD), reply(GOOD)]
    r = run(make_task(ADD_TESTS), model_spec)
    assert [a.status for a in r.attempts] == ["failed", "repeat", "passed"]
    assert r.repeats == 1
    assert "EXACTLY the same code" in script.calls[2]["prompt"]


def test_temperature_rises_on_retries(make_task, script, model_spec):
    script.replies = [reply(BAD), reply({"solution.py": "def add(a, b):\n    return 0\n"}), reply(GOOD)]
    run(make_task(ADD_TESTS), model_spec)
    assert [c["temperature"] for c in script.calls] == [0.0, 0.5, 0.8]


def test_no_anti_stuck_keeps_temperature_and_reruns_repeats(make_task, script, model_spec):
    script.replies = [reply(BAD), reply(BAD), reply(GOOD)]
    r = run(make_task(ADD_TESTS), model_spec, anti_stuck=False)
    assert [a.status for a in r.attempts] == ["failed", "failed", "passed"]
    assert {c["temperature"] for c in script.calls} == {0.0}


def test_unsafe_code_is_blocked_and_not_run(make_task, script, model_spec, tmp_path):
    marker = tmp_path / "pwned"
    evil = {"solution.py": f"import os\nos.system('touch {marker}')\ndef add(a, b):\n    return a + b\n"}
    script.replies = [reply(evil), reply(GOOD)]
    r = run(make_task(ADD_TESTS), model_spec)
    assert [a.status for a in r.attempts] == ["blocked", "passed"]
    assert not marker.exists(), "blocked code must never run"
    assert r.attempts[0].violations and "blocked by the safety check" in script.calls[1]["prompt"]


def test_blocked_until_the_end(make_task, script, model_spec):
    evil = {"solution.py": "import subprocess\ndef add(a, b):\n    return a + b\n"}
    script.replies = [reply(evil)]
    r = run(make_task(ADD_TESTS), model_spec, max_attempts=1)
    assert r.status == "blocked" and r.best_passed == 0 and r.total == 3


def test_task_allow_imports(make_task, script, model_spec):
    code = {"solution.py": "import subprocess  # allowed by the task\ndef add(a, b):\n    return a + b\n"}
    script.replies = [reply(code)]
    r = run(make_task(ADD_TESTS, allow_imports="[subprocess]"), model_spec)
    assert r.status == "passed"


def test_invalid_reply_gets_format_help(make_task, script, model_spec):
    script.replies = ["Sorry, I can't.", reply(GOOD)]
    r = run(make_task(ADD_TESTS), model_spec)
    assert [a.status for a in r.attempts] == ["invalid", "passed"]
    assert "FILE: path/to/file.py" in script.calls[1]["prompt"]


def test_plan_first_order_and_plan_in_prompt(make_task, script, model_spec):
    script.replies = ["RULES: 1. add numbers", reply(BAD), "RULES: 1. really add", reply(GOOD)]
    r = run(make_task(ADD_TESTS), model_spec, plan_first=True)
    assert r.status == "passed"
    kinds = ["plan" if "Do NOT write code yet" in c["prompt"] else "code" for c in script.calls]
    assert kinds == ["plan", "code", "plan", "code"]
    assert "really add" in script.calls[3]["prompt"] and "Your previous plan" in script.calls[2]["prompt"]
    assert r.attempts[1].plan == "RULES: 1. really add"


def test_multi_file_changes_accumulate(make_task, script, model_spec):
    tests = """
        from pkg.a import one
        from pkg.b import two
        def test_one():
            assert one() == 1
        def test_two():
            assert two() == 2
    """
    task = make_task(tests, files="[pkg/a.py, pkg/b.py]", starter={"pkg/__init__.py": ""})
    script.replies = [
        reply({"pkg/a.py": "def one():\n    return 1\n", "pkg/b.py": "def two():\n    return 3\n"}),
        reply({"pkg/b.py": "def two():\n    return 2\n"}),      # only the file that changed
    ]
    r = run(task, model_spec)
    assert r.status == "passed"
    assert set(r.best_files) == {"pkg/a.py", "pkg/b.py"}
    assert "FILE: pkg/a.py" in script.calls[1]["prompt"], "retry prompt shows the current files"


def test_safety_override(make_task, script, model_spec):
    code = {"solution.py": "import sys\ndef add(a, b):\n    return a + b\n"}
    script.replies = [reply(code)]
    assert run(make_task(ADD_TESTS), model_spec).status == "passed"
    script.replies = [reply(code)]
    assert run(make_task(ADD_TESTS), model_spec, safety="strict", max_attempts=1).status == "blocked"
