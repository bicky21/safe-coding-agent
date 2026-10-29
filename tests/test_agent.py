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


def test_invalid_and_repeat_do_not_use_up_attempts(make_task, script, model_spec):
    script.replies = ["no code here", reply(BAD), reply(BAD), reply(GOOD)]
    r = run(make_task(ADD_TESTS), model_spec, max_attempts=2)
    assert [a.status for a in r.attempts] == ["invalid", "failed", "repeat", "passed"]
    assert r.status == "passed"


def test_unusable_answers_stop_early(make_task, script, model_spec):
    script.replies = ["no code"] * 10
    r = run(make_task(ADD_TESTS), model_spec, max_attempts=5)
    assert len(r.attempts) == 3 and r.status == "failed"   # 3 unusable answers in a row: give up


def test_model_calls_are_capped(make_task, script, model_spec):
    other = {"solution.py": "def add(a, b):\n    return 0\n"}
    script.replies = ["no code", reply(BAD), "no code", reply(other), "no code", "no code"]
    r = run(make_task(ADD_TESTS), model_spec, max_attempts=3)
    assert len(r.attempts) <= 6


def test_raw_reply_is_kept(make_task, script, model_spec):
    script.replies = ["I think the answer is 42.", reply(GOOD)]
    r = run(make_task(ADD_TESTS), model_spec)
    assert r.attempts[0].reply == "I think the answer is 42."


def test_change_that_fixes_nothing_is_called_out(make_task, script, model_spec):
    cosmetic = {"solution.py": "def add(a, b):\n    # rewritten\n    return a - b\n"}   # same bug
    script.replies = [reply(BAD), reply(cosmetic), reply(GOOD)]
    r = run(make_task(ADD_TESTS), model_spec)
    assert [a.status for a in r.attempts] == ["failed", "failed", "passed"]
    assert "did NOT fix anything" in script.calls[2]["prompt"]
    assert "did NOT fix anything" not in script.calls[1]["prompt"]


def test_ollama_gets_a_context_window_that_fits(make_task, script, monkeypatch):
    from safe_coding_agent import agent as agent_mod
    from safe_coding_agent.models import parse_model
    seen = []
    real = agent_mod.make_model
    monkeypatch.setattr(agent_mod, "make_model", lambda spec, t: (seen.append(spec.num_ctx), real(
        parse_model("scripted:x"), t))[1])
    script.replies = [reply(GOOD)]
    big = {"lib/big.py": "x = 1\n" * 3000}                              # ~18k chars -> needs > 4096 tokens
    CodingAgent(load_task(make_task(ADD_TESTS, starter=big)), Settings(model=parse_model("ollama:fake")),
                LocalRunner()).run()
    assert seen and seen[0] >= 8192


def test_repeat_triggers_a_fresh_start(make_task, script, model_spec):
    starter = {"lib/helper.py": "HELPER = 1\n"}
    script.replies = [reply(BAD), reply(BAD), reply(GOOD)]
    r = run(make_task(ADD_TESTS, starter=starter), model_spec)
    assert [a.status for a in r.attempts] == ["failed", "repeat", "passed"]
    after_repeat = script.calls[2]["prompt"]
    assert "STARTING OVER" in after_repeat
    assert "return a - b" not in after_repeat.split("Your previous attempt failed")[0], \
        "the failed code must not be shown again as the current project"
    assert "FILE: lib/helper.py" in after_repeat


def test_two_repeats_in_a_row_stop_early(make_task, script, model_spec):
    script.replies = [reply(BAD), reply(BAD), reply(BAD), reply(GOOD)]
    r = run(make_task(ADD_TESTS), model_spec, max_attempts=3)
    assert [a.status for a in r.attempts] == ["failed", "repeat", "repeat"]
    assert len(script.calls) == 3


def test_best_files_are_exactly_what_was_tested(make_task, script, model_spec):
    tests = """
        from pkg.a import one
        def test_one():
            assert one() == 1
    """
    task = make_task(tests, files="[pkg/a.py, pkg/b.py]", starter={"pkg/__init__.py": ""})
    first = {"pkg/a.py": "def one():\n    return 2\n", "pkg/b.py": "OLD = 1\n"}
    script.replies = [reply(first), reply(first), reply({"pkg/a.py": "def one():\n    return 1\n"})]
    r = run(task, model_spec)
    assert r.status == "passed"
    assert r.best_files == {"pkg/a.py": "def one():\n    return 1\n"}, "b.py was dropped by the fresh start"


def test_model_error_stops_the_task_but_keeps_earlier_attempts(make_task, script, model_spec):
    script.replies = [reply(BAD), "RAISE:401 invalid api key"]
    r = run(make_task(ADD_TESTS), model_spec)
    assert [a.status for a in r.attempts] == ["failed", "error"]
    assert r.status == "error" and r.best_passed == 1 and "401" in r.attempts[-1].feedback


def test_model_error_while_planning(make_task, script, model_spec):
    script.replies = ["RAISE:401 invalid api key"]
    r = run(make_task(ADD_TESTS), model_spec, plan_first=True)
    assert r.status == "error" and len(script.calls) == 1


def test_too_large_request_retries_with_shorter_answer(make_task, script):
    from safe_coding_agent.models import parse_model, register_provider

    from .conftest import ScriptedModel
    seen = []

    def factory(spec, temperature):
        seen.append(spec.max_tokens)
        if spec.max_tokens > 4096:
            class TooBig(ScriptedModel):
                def _generate(self, *a, **k):
                    raise RuntimeError("Error code: 413 - Request too large ... tokens per minute (TPM)")
            return TooBig()
        return ScriptedModel()

    register_provider("tiny-tier", factory)
    script.replies = [reply(GOOD)]
    r = run(make_task(ADD_TESTS), parse_model("tiny-tier:m", max_tokens=8192))
    assert r.status == "passed" and seen == [8192, 4096]
