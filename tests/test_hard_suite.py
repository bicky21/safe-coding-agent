"""The hard suite must be correct: every task's reference solution (kept here in tests/, never
shown to the agent) passes all of its tests, and an empty answer passes almost none."""

from pathlib import Path

import pytest

from safe_coding_agent.safety import check_files
from safe_coding_agent.sandbox import LocalRunner, summarize_output
from safe_coding_agent.tasks import builtin_suite_dir, load_suite, read_tree

REFERENCE = Path(__file__).parent / "hard_reference"
TASKS = load_suite(builtin_suite_dir("hard"))


def test_suite_contents():
    assert {t.name for t in TASKS} == {"template-engine", "config-parser", "recurring-events",
                                       "inventory-ledger", "expression-eval"}
    assert all(t.level == "project" for t in TASKS)
    assert sum(t.count_tests() for t in TASKS) >= 150


@pytest.mark.parametrize("task", TASKS, ids=[t.name for t in TASKS])
def test_reference_solution_passes_everything(task):
    files = read_tree(REFERENCE / task.name)
    assert set(task.files) <= set(files), "the reference must write every expected file"
    assert check_files(files, task.allow_imports, task.safety) == []
    result = LocalRunner().run(task, files)
    assert result.all_passed, summarize_output(result.output)
    assert result.total == task.count_tests()


@pytest.mark.parametrize("task", TASKS, ids=[t.name for t in TASKS])
def test_no_solution_fails(task):
    result = LocalRunner().run(task, {})
    assert result.passed <= 1


def test_named_suites():
    from safe_coding_agent.tasks import TaskError, resolve_suite
    assert resolve_suite(None)[1] == "builtin" and resolve_suite("hard")[1] == "hard"
    with pytest.raises(TaskError, match="no such folder"):
        load_suite("definitely-not-here")
