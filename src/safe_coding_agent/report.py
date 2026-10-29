"""Saving runs and comparing them.

Each `sca run` / `sca bench` writes one folder:

    sca-runs/20261029-150000-bench/
      summary.json      settings + scores (what `sca compare` reads)
      results.csv       one row per task per run
      log.md            every attempt: plan, code, test feedback
      attempts.jsonl    the same, machine-readable
      solutions/        the best code for every task
"""

from __future__ import annotations

import csv
import json
import re
import time
from collections import defaultdict
from pathlib import Path

from . import __version__
from .agent import TaskResult

FIELDS = ["run", "task", "level", "status", "attempts", "repeats", "blocked",
          "first_passed", "best_passed", "total", "seconds"]


def new_run_dir(base: str | Path, label: str) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", label).strip("-")[:40] or "run"
    path = Path(base) / f"{stamp}-{safe}"
    n = 2
    while path.exists():
        path = Path(base) / f"{stamp}-{safe}-{n}"
        n += 1
    path.mkdir(parents=True)
    return path


def totals(results: list[TaskResult]) -> dict:
    return {
        "tasks": len(results),
        "tasks_passed": sum(r.status == "passed" for r in results),
        "tests_total": sum(r.total for r in results),
        "tests_first": sum(r.first_passed for r in results),
        "tests_best": sum(r.best_passed for r in results),
        "repeats": sum(r.repeats for r in results),
        "blocked": sum(r.blocked for r in results),
        "seconds": round(sum(r.seconds for r in results), 1),
    }


def save(run_dir: Path, runs: list[list[TaskResult]], settings: dict, suite: str,
         runner: str) -> None:
    summary = {
        "version": __version__, "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "settings": settings, "suite": suite, "runner": runner,
        "tasks": sorted({r.task for rs in runs for r in rs}),
        "runs": [totals(rs) for rs in runs],
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    with open(run_dir / "results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for k, rs in enumerate(runs, 1):
            for r in rs:
                w.writerow({"run": k, "task": r.task, "level": r.level, "status": r.status,
                            "attempts": len(r.attempts), "repeats": r.repeats, "blocked": r.blocked,
                            "first_passed": r.first_passed, "best_passed": r.best_passed,
                            "total": r.total, "seconds": r.seconds})

    with open(run_dir / "attempts.jsonl", "w", encoding="utf-8") as f:
        for k, rs in enumerate(runs, 1):
            for r in rs:
                for a in r.attempts:
                    f.write(json.dumps({"run": k, "task": r.task, **a.to_dict()}) + "\n")

    with open(run_dir / "log.md", "w", encoding="utf-8") as f:
        f.write(f"# Run log\n\nSettings: {json.dumps(settings)}\n\nRunner: {runner}\n")
        for k, rs in enumerate(runs, 1):
            if len(runs) > 1:
                f.write(f"\n# Run {k} of {len(runs)}\n")
            for r in rs:
                f.write(f"\n## {r.task} ({r.level}): {r.status}, best {r.best_passed}/{r.total} tests\n")
                for a in r.attempts:
                    f.write(f"\n### Attempt {a.number}: {a.status} ({a.passed}/{a.total} tests, {a.seconds}s)\n\n")
                    if a.plan:
                        f.write("Plan:\n\n" + _fence(a.plan, "text") + "\n")
                    for path, text in a.files.items():
                        f.write(f"File `{path}`:\n\n" + _fence(text, "python" if path.endswith(".py") else "") + "\n")
                    f.write("Feedback:\n\n" + _fence(a.feedback, "") + "\n")

    for k, rs in enumerate(runs, 1):
        for r in rs:
            base = run_dir / "solutions" / (f"run{k}" if len(runs) > 1 else "") / r.task
            write_files(base, r.best_files)


def write_files(base: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        target = (base / rel).resolve()
        if base.resolve() not in target.parents:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _fence(text: str, lang: str) -> str:
    ticks = "```"
    while ticks in text:
        ticks += "`"
    return f"{ticks}{lang}\n{text}\n{ticks}\n"


# ---------------------------------------------------------------- compare

def method_label(s: dict) -> str:
    if s.get("max_attempts") == 1:
        return "no self-checking (1 attempt)"
    parts = ["plan-first"] if s.get("plan_first") else []
    parts.append("anti-stuck" if s.get("anti_stuck") else "no anti-stuck")
    parts.append(f"{s.get('feedback')} feedback")
    parts.append(f"max {s.get('max_attempts')}")
    if s.get("safety") not in (None, "task default"):
        parts.append(f"safety {s['safety']}")
    return ", ".join(parts)


def compare(runs_dir: str | Path, task_filter: str | None = None) -> list[dict]:
    """Group every saved run by model + method + task set; average the scores."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for summary_file in sorted(Path(runs_dir).glob("*/summary.json")):
        try:
            data = json.loads(summary_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if task_filter and task_filter not in data.get("suite", "") and task_filter not in data.get("tasks", []):
            continue
        s = data["settings"]
        key = (s["model"], data.get("suite", "?"), len(data.get("tasks", [])), method_label(s))
        groups[key].extend(data["runs"])
    rows = []
    for (model, suite, n_tasks, method), runs in sorted(groups.items()):
        bests = [r["tests_best"] for r in runs]
        n = len(runs)
        rows.append({
            "model": model, "suite": suite, "tasks": n_tasks, "method": method, "runs": n,
            "tasks_passed": sum(r["tasks_passed"] for r in runs) / n,
            "tests_total": runs[0]["tests_total"],
            "first": sum(r["tests_first"] for r in runs) / n,
            "best": sum(bests) / n, "best_min": min(bests), "best_max": max(bests),
            "minutes": sum(r["seconds"] for r in runs) / n / 60,
        })
    return rows
