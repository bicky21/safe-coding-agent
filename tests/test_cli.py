import csv
import json
from pathlib import Path

from safe_coding_agent.cli import main
from safe_coding_agent.tasks import load_task

from .conftest import ADD_TESTS, reply

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "todo-project"

TODO_STORE_ADDITIONS = '''
    def _get(self, item_id: int) -> Item:
        if item_id not in self._items:
            raise KeyError(item_id)
        return self._items[item_id]

    def complete(self, item_id: int) -> None:
        self._get(item_id).done = True

    def remove(self, item_id: int) -> None:
        self._get(item_id)
        del self._items[item_id]

    def pending(self) -> list[Item]:
        return sorted((i for i in self._items.values() if not i.done), key=lambda i: (-i.priority, i.id))
'''

TODO_REPORT = '''from todo.store import TodoStore


def summary(store: TodoStore) -> str:
    items = store.items()
    done = sum(i.done for i in items)
    pending = store.pending()
    word = "task" if len(items) == 1 else "tasks"
    tail = f"Next: {pending[0].title}" if pending else "Nothing pending."
    return f"{len(items)} {word}: {done} done, {len(pending)} pending. {tail}"
'''

COMMON = ["--model", "scripted:test", "--runner", "local", "-q"]


def test_run_example_project(script, tmp_path, capsys):
    store = (EXAMPLE / "starter" / "todo" / "store.py").read_text() + TODO_STORE_ADDITIONS
    script.replies = [
        reply({"todo/store.py": store}),                                   # forgot report.py
        reply({"todo/report.py": TODO_REPORT}),                            # adds it
    ]
    out_dir = tmp_path / "out"
    code = main(["run", str(EXAMPLE), *COMMON, "--runs-dir", str(tmp_path / "runs"), "--out", str(out_dir)])
    assert code == 0
    text = capsys.readouterr().out
    assert "9/13" in text and "13/13" in text
    assert (out_dir / "todo" / "report.py").read_text() == TODO_REPORT
    [run_dir] = list((tmp_path / "runs").iterdir())
    for name in ("summary.json", "results.csv", "log.md", "attempts.jsonl"):
        assert (run_dir / name).is_file()
    assert (run_dir / "solutions" / "todo-project" / "todo" / "store.py").is_file()
    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["runs"][0]["tests_best"] == 13 and summary["runs"][0]["tests_first"] == 9


def test_run_fails_with_exit_code_1(make_task, script, tmp_path):
    script.replies = [reply({"solution.py": "def add(a, b):\n    return 0\n"})]
    code = main(["run", str(make_task(ADD_TESTS)), *COMMON, "--max-attempts", "1",
                 "--runs-dir", str(tmp_path / "runs")])
    assert code == 1


def test_bench_runs_and_compare(script, tmp_path, capsys):
    good = reply({"solution.py": "def roman_to_int(s):\n    v = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, "
                                 "'D': 500, 'M': 1000}\n    t = 0\n    for i, c in enumerate(s):\n"
                                 "        t += -v[c] if i + 1 < len(s) and v[c] < v[s[i + 1]] else v[c]\n"
                                 "    return t\n"})
    bad = reply({"solution.py": "def roman_to_int(s):\n    return len(s)\n"})
    script.replies = [bad, good, good]
    runs = str(tmp_path / "runs")
    assert main(["bench", "--task", "roman", "--runs", "2", *COMMON, "--runs-dir", runs]) == 0
    [run_dir] = list(Path(runs).iterdir())
    rows = list(csv.DictReader(open(run_dir / "results.csv")))
    assert [(r["run"], r["status"], r["attempts"]) for r in rows] == [("1", "passed", "2"), ("2", "passed", "1")]
    capsys.readouterr()
    assert main(["compare", "--runs-dir", runs]) == 0
    table = capsys.readouterr().out
    assert "scripted:test" in table and "anti-stuck, detailed feedback, max 3" in table


def test_bench_unknown_task(tmp_path, capsys):
    assert main(["bench", "--task", "nope", *COMMON, "--runs-dir", str(tmp_path)]) == 2
    assert "unknown task" in capsys.readouterr().err


def test_new_task_creates_a_valid_task(tmp_path):
    assert main(["new-task", "greet", "--dir", str(tmp_path)]) == 0
    task = load_task(tmp_path / "greet")
    assert task.name == "greet" and task.count_tests() == 2


def test_check_command(tmp_path, capsys):
    good, bad = tmp_path / "good.py", tmp_path / "bad.py"
    good.write_text("import math\nprint(math.pi)\n")
    bad.write_text("import os\nos.system('ls')\n")
    assert main(["check", str(good)]) == 0
    assert main(["check", str(bad)]) == 1
    assert "os.system" in capsys.readouterr().out


def test_list_builtin(capsys):
    assert main(["list"]) == 0
    assert len(capsys.readouterr().out.strip().splitlines()) == 13


def test_bad_model_spec(capsys, tmp_path):
    assert main(["bench", "--model", "gemma3", "--runs-dir", str(tmp_path)]) == 2
    assert "provider:name" in capsys.readouterr().err


def test_bench_survives_a_model_error_and_saves_results(script, tmp_path, capsys):
    ok = reply({"solution.py": "def is_palindrome(s):\n    t = [c.lower() for c in s if c.isalnum()]\n"
                               "    return t == t[::-1]\n"})
    script.replies = [ok, "RAISE:Error code: 401 - Invalid API Key"]
    runs = str(tmp_path / "runs")
    code = main(["bench", "--task", "palindrome", "--task", "roman", *COMMON, "--runs-dir", runs])
    assert code == 0
    [run_dir] = list(Path(runs).iterdir())
    rows = {r["task"]: r["status"] for r in csv.DictReader(open(run_dir / "results.csv"))}
    assert rows == {"palindrome": "passed", "roman": "error"}
