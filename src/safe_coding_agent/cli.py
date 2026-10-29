"""Command line: `sca`.

    sca run TASK_DIR            solve one task (your own or a built-in one)
    sca bench                   run a whole suite (default: the built-in benchmark)
    sca compare                 compare all saved runs side by side
    sca new-task NAME           create a new task folder from a template
    sca list                    list the tasks in a suite
    sca check FILE...           run the safety check on your own files
    sca sandbox build|status    build / check the Docker sandbox
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import __version__, report
from .agent import CodingAgent, Settings, TaskResult
from .models import ModelError, parse_model, preflight
from .safety import check_source
from .sandbox import SANDBOX_IMAGE, SandboxError, build_image, docker_status, get_runner
from .tasks import TaskError, builtin_suite_dir, load_suite, load_task

DEFAULT_MODEL = "ollama:gemma3:4b"
_print_lock = threading.Lock()


def out(msg: str = "") -> None:
    with _print_lock:
        print(msg, flush=True)


# ---------------------------------------------------------------- shared options

def add_agent_options(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("model")
    g.add_argument("-m", "--model", default=os.environ.get("SCA_MODEL", DEFAULT_MODEL),
                   help="provider:name, e.g. ollama:gemma3:4b, openai:gpt-4o-mini, "
                        "anthropic:claude-sonnet-5-5 (env SCA_MODEL; default %(default)s)")
    g.add_argument("--base-url", help="API base URL (OpenAI-compatible servers, remote Ollama)")
    g.add_argument("--api-key-env", help="name of the env variable holding the API key")
    g.add_argument("--max-tokens", type=int, default=8192, help="max tokens per model reply")
    g = p.add_argument_group("agent")
    g.add_argument("--max-attempts", type=int, default=3,
                   help="real tries per task (1 = no self-checking); unusable answers and repeats don't count")
    g.add_argument("--plan", action="store_true", help="plan first: rules, worked examples, steps")
    g.add_argument("--feedback", choices=["detailed", "simple"], default="detailed",
                   help="detailed = full pytest failure output; simple = failing test names only")
    g.add_argument("--no-anti-stuck", action="store_true",
                   help="allow repeated code and keep temperature 0 on retries")
    g.add_argument("--context-chars", type=int, default=120_000,
                   help="max characters of existing code to put in one prompt")
    g = p.add_argument_group("safety & sandbox")
    g.add_argument("--safety", choices=["standard", "strict", "off"],
                   help="override every task's safety level")
    g.add_argument("--runner", choices=["auto", "docker", "local"], default="auto",
                   help="where tests run (auto = Docker if ready, else local)")
    g.add_argument("--image", default=SANDBOX_IMAGE, help="Docker sandbox image")
    g.add_argument("--timeout", type=int, help="override every task's test timeout (seconds)")
    g = p.add_argument_group("output")
    g.add_argument("--runs-dir", default="sca-runs", help="where results are saved (default %(default)s)")
    g.add_argument("-q", "--quiet", action="store_true", help="only print the summary")


def make_settings(a) -> Settings:
    spec = parse_model(a.model, a.base_url, a.api_key_env, a.max_tokens)
    if a.max_attempts < 1:
        raise SystemExit("--max-attempts must be at least 1")
    return Settings(model=spec, max_attempts=a.max_attempts, feedback=a.feedback,
                    anti_stuck=not a.no_anti_stuck, plan_first=a.plan, safety=a.safety,
                    context_chars=a.context_chars, timeout=a.timeout)


def make_runner(a):
    runner, note = get_runner(a.runner, a.image)
    if note:
        out(f"WARNING: {note}")
    return runner


def solve(task, settings, runner, quiet: bool, prefix: str = "") -> TaskResult:
    say = (lambda m: None) if quiet else (lambda m: out(f"  {prefix}{task.name}: {m}"))
    return CodingAgent(task, settings, runner, on_event=say).run()


def print_table(results: list[TaskResult]) -> None:
    out(f"\n{'task':<20}{'level':<9}{'status':<9}{'tries':>6}{'repeats':>8}{'blocked':>8}"
        f"{'first':>8}{'best':>8}{'secs':>8}")
    out("-" * 84)
    for r in results:
        out(f"{r.task[:19]:<20}{r.level[:8]:<9}{r.status:<9}{len(r.attempts):>6}{r.repeats:>8}"
            f"{r.blocked:>8}{f'{r.first_passed}/{r.total}':>8}{f'{r.best_passed}/{r.total}':>8}"
            f"{r.seconds:>8.0f}")
    t = report.totals(results)
    out("-" * 84)
    out(f"Tasks passed: {t['tasks_passed']}/{t['tasks']}    Tests: first try {t['tests_first']}/"
        f"{t['tests_total']}, best {t['tests_best']}/{t['tests_total']}    "
        f"Repeats: {t['repeats']}    Blocked: {t['blocked']}")


# ---------------------------------------------------------------- commands

def cmd_run(a) -> int:
    task = load_task(a.task)
    settings = make_settings(a)
    preflight(settings.model)
    runner = make_runner(a)
    out(f"Task: {task.name}   Model: {settings.model.label}   Runner: {runner.name}   "
        f"Max attempts: {settings.max_attempts}" + ("   Plan-first" if settings.plan_first else ""))
    result = solve(task, settings, runner, a.quiet)
    print_table([result])
    run_dir = report.new_run_dir(a.runs_dir, task.name)
    report.save(run_dir, [[result]], settings.describe(), suite=str(task.path), runner=runner.name)
    if a.out and result.best_files:
        report.write_files(Path(a.out), result.best_files)
        out(f"Best code written to: {a.out}")
    out(f"Saved: {run_dir}   (best code in {run_dir / 'solutions' / task.name})")
    return 0 if result.status == "passed" else 1


def _select(tasks, a):
    if a.level:
        tasks = [t for t in tasks if t.level == a.level]
    if a.task:
        wanted = set(a.task)
        unknown = wanted - {t.name for t in tasks}
        if unknown:
            raise TaskError(f"unknown task(s): {', '.join(sorted(unknown))} (see: sca list)")
        tasks = [t for t in tasks if t.name in wanted]
    if not tasks:
        raise TaskError("no tasks selected")
    return tasks


def cmd_bench(a) -> int:
    suite_dir = Path(a.suite) if a.suite else builtin_suite_dir()
    tasks = _select(load_suite(suite_dir), a)
    settings = make_settings(a)
    preflight(settings.model)
    runner = make_runner(a)
    suite_label = "builtin" if not a.suite else str(suite_dir.resolve())
    if a.level:
        suite_label += f":{a.level}"
    out(f"Suite: {suite_label} ({len(tasks)} tasks)   Model: {settings.model.label}   Runner: {runner.name}   "
        f"Runs: {a.runs}   Jobs: {a.jobs}" + ("   Plan-first" if settings.plan_first else ""))
    runs: list[list[TaskResult]] = []
    for k in range(1, a.runs + 1):
        if a.runs > 1:
            out(f"\n===== run {k} of {a.runs} =====")
        prefix = f"[run {k}] " if a.runs > 1 else ""
        if a.jobs > 1:
            with ThreadPoolExecutor(max_workers=a.jobs) as pool:
                results = list(pool.map(lambda t, p=prefix: solve(t, settings, runner, a.quiet, p), tasks))
        else:
            results = [solve(t, settings, runner, a.quiet, prefix) for t in tasks]
        print_table(results)
        runs.append(results)
    if a.runs > 1:
        out("\nAll runs:")
        for k, rs in enumerate(runs, 1):
            t = report.totals(rs)
            out(f"  run {k}: tasks {t['tasks_passed']}/{t['tasks']}   tests first {t['tests_first']}/"
                f"{t['tests_total']}   best {t['tests_best']}/{t['tests_total']}")
    run_dir = report.new_run_dir(a.runs_dir, "bench" + (f"-{a.level}" if a.level else ""))
    report.save(run_dir, runs, settings.describe(), suite=suite_label, runner=runner.name)
    out(f"\nSaved: {run_dir}\nCompare methods with: sca compare --runs-dir {a.runs_dir}")
    return 0


def cmd_compare(a) -> int:
    rows = report.compare(a.runs_dir, a.filter)
    if not rows:
        out(f"No saved runs found in {a.runs_dir}/ (run `sca bench` first).")
        return 1
    out(f"\n{'model':<26}{'suite':<18}{'method':<44}{'runs':>5}{'tasks':>9}{'first try':>12}"
        f"{'best':>10}{'range':>9}{'min/run':>9}")
    out("-" * 142)
    for r in rows:
        t = r["tests_total"]
        tasks = f"{r['tasks_passed']:.1f}/{r['tasks']}"
        first = f"{r['first']:.1f}/{t}"
        best = f"{r['best']:.1f}/{t}"
        rng = f"{r['best_min']}-{r['best_max']}"
        out(f"{r['model'][:25]:<26}{r['suite'][-17:]:<18}{r['method'][:43]:<44}{r['runs']:>5}"
            f"{tasks:>9}{first:>12}{best:>10}{rng:>9}{r['minutes']:>9.1f}")
    out("\nfirst try = without self-checking; best = with self-checking. If two methods differ by less "
        "than their range, the difference is probably luck.")
    return 0


TASK_TEMPLATE = """name: {name}
level: custom
prompt: |
  Write a function greet(name: str) -> str in solution.py that returns "Hello, <name>!".
  An empty name should return "Hello, world!".
files: [solution.py]     # files the model should write
timeout: 60              # seconds for one test run
show_tests: false        # true = the model sees the tests
safety: standard         # standard | strict | off
allow_imports: []        # e.g. [subprocess] if the task really needs it
"""

TEST_TEMPLATE = '''import pytest

from solution import greet


@pytest.mark.parametrize("name, expected", [
    ("Ana", "Hello, Ana!"),
    ("", "Hello, world!"),
])
def test_greet(name, expected):
    assert greet(name) == expected
'''


def cmd_new_task(a) -> int:
    folder = Path(a.dir) / a.name
    if folder.exists():
        raise TaskError(f"{folder} already exists")
    (folder / "tests").mkdir(parents=True)
    (folder / "starter").mkdir()
    (folder / "task.yaml").write_text(TASK_TEMPLATE.format(name=a.name), encoding="utf-8")
    (folder / "tests" / "test_solution.py").write_text(TEST_TEMPLATE, encoding="utf-8")
    (folder / "starter" / "README.md").write_text(
        "Put existing code the model should build on in this folder (optional).\n", encoding="utf-8")
    out(f"Created {folder}/\n  task.yaml          edit the prompt and settings\n"
        f"  tests/             your pytest tests (the model can't change them)\n"
        f"  starter/           optional existing code\nThen run:  sca run {folder}")
    return 0


def cmd_list(a) -> int:
    suite_dir = Path(a.suite) if a.suite else builtin_suite_dir()
    for t in load_suite(suite_dir):
        out(f"{t.name:<20}{t.level:<10}{t.count_tests():>4} tests   {t.path}")
    return 0


def cmd_check(a) -> int:
    bad = 0
    for f in a.files:
        text = Path(f).read_text(encoding="utf-8")
        found = check_source(text, f, a.allow, a.safety)
        for v in found:
            out(str(v))
        bad += len(found)
    out(f"{bad} problem(s) found" if bad else "No problems found.")
    return 1 if bad else 0


def cmd_sandbox(a) -> int:
    if a.action == "status":
        ok, why = docker_status(a.image)
        out(why)
        return 0 if ok else 1
    if not shutil.which("docker"):
        out("Docker is not installed. See https://docs.docker.com/engine/install/")
        return 1
    code = build_image(a.image, a.base, a.package)
    out("Sandbox image ready." if code == 0 else "Building the sandbox image failed.")
    return code


# ---------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sca", description="Self-checking, sandboxed coding agent.")
    p.add_argument("--version", action="version", version=f"safe-coding-agent {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="solve one task folder")
    r.add_argument("task", help="path to a task folder (contains task.yaml)")
    r.add_argument("--out", help="also copy the best code into this folder")
    add_agent_options(r)
    r.set_defaults(func=cmd_run)

    b = sub.add_parser("bench", help="run a suite of tasks (default: built-in benchmark)")
    b.add_argument("--suite", help="folder of task folders (default: built-in benchmark)")
    b.add_argument("--level", help="only tasks with this level, e.g. tricky")
    b.add_argument("--task", action="append", help="only this task (repeatable)")
    b.add_argument("--runs", type=int, default=1, help="repeat the whole suite N times")
    b.add_argument("--jobs", type=int, default=1, help="tasks in parallel (good for API models)")
    add_agent_options(b)
    b.set_defaults(func=cmd_bench)

    c = sub.add_parser("compare", help="compare saved runs")
    c.add_argument("--runs-dir", default="sca-runs")
    c.add_argument("--filter", help="only runs whose suite or tasks match this text")
    c.set_defaults(func=cmd_compare)

    n = sub.add_parser("new-task", help="create a task folder from a template")
    n.add_argument("name")
    n.add_argument("--dir", default=".", help="where to create it")
    n.set_defaults(func=cmd_new_task)

    ls = sub.add_parser("list", help="list tasks in a suite")
    ls.add_argument("--suite", help="folder of task folders (default: built-in benchmark)")
    ls.set_defaults(func=cmd_list)

    ck = sub.add_parser("check", help="run the safety check on Python files")
    ck.add_argument("files", nargs="+")
    ck.add_argument("--safety", choices=["standard", "strict"], default="standard")
    ck.add_argument("--allow", action="append", default=[], help="allow this module (repeatable)")
    ck.set_defaults(func=cmd_check)

    sb = sub.add_parser("sandbox", help="Docker sandbox: build the image or check status")
    sb.add_argument("action", choices=["build", "status"])
    sb.add_argument("--image", default=SANDBOX_IMAGE)
    sb.add_argument("--base", default="python:3.12-slim", help="base image to build from")
    sb.add_argument("--package", action="append", help="extra pip package for the image (repeatable)")
    sb.set_defaults(func=cmd_sandbox)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (TaskError, ModelError, SandboxError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nstopped", file=sys.stderr)
        return 130
    except BrokenPipeError:  # output piped into e.g. `head`, which closed early
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        return 0


if __name__ == "__main__":
    sys.exit(main())
