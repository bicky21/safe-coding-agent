"""
Compare methods across all runs in results/.

Groups every run by its settings (model, feedback, max attempts, anti-stuck, plan-first,
which levels) and shows, per method:
  - runs        how many runs of this method there are
  - tasks       average tasks fully passed per run
  - first try   average tests passed by attempt 1 (= what you get WITHOUT self-checking)
  - best        average tests passed by the best attempt (= WITH self-checking)
  - best range  lowest-highest "best" over the runs (shows how much luck is involved)

Older results without test scores are re-scored from their .log.md files.

Usage:
  python compare.py                 # all results
  python compare.py --level tricky  # only runs on the tricky tasks
"""

import argparse
import csv
import glob
import os
import re
from collections import defaultdict

from agent import score_code
from tasks import TASKS

TESTS = {t["name"]: t["tests"] for t in TASKS}


def rescore_from_log(log_path: str) -> dict:
    """Old logs: score each task's attempts. Returns {(run, task): (first, best, total)}."""
    text = open(log_path, encoding="utf-8").read()
    out = {}
    run_parts = re.split(r"\n# Run (\d+) of \d+\n", text)
    chunks = [(1, run_parts[0])] if len(run_parts) == 1 else [
        (int(run_parts[i]), run_parts[i + 1]) for i in range(1, len(run_parts), 2)]
    heading = r"\n## (?=\S+ \((?:easy|medium|hard|tricky)\): \w+\n)"
    for run, chunk in chunks:
        for section in re.split(heading, chunk)[1:]:
            task = section.split()[0]
            codes = re.findall(r"### Attempt \d+\n\n(?:Plan:\n\n```text\n.*?\n```\n\n)?"
                               r"```python\n(.*?)\n```\n\nResult[^\n]*:\n\n```\n(.*?)\n```",
                               section, re.S)
            cache, scores = {}, []
            for code, result in codes:
                if result.startswith("Blocked:"):
                    scores.append((0, score_code("", TESTS[task])[1]))
                    continue
                key = code.strip()
                if key not in cache:
                    cache[key] = score_code(code, TESTS[task])
                scores.append(cache[key])
            if scores:
                out[(run, task)] = (scores[0][0], max(p for p, _ in scores), scores[0][1])
    return out


def method_name(row: dict) -> str:
    if row.get("max_attempts") == "1":
        return "no self-checking (1 attempt)"
    parts = []
    if row.get("plan_first") == "True":
        parts.append("plan-first")
    parts.append("anti-stuck" if row.get("anti_stuck", "False") == "True" else "no anti-stuck")
    parts.append(f"{row.get('feedback', 'simple')} feedback")
    parts.append(f"max {row.get('max_attempts')}")
    return ", ".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", help="only include runs on this level (e.g. tricky)")
    args = parser.parse_args()

    groups = defaultdict(list)   # method -> list of runs; each run = list of task rows
    skipped = 0
    for path in sorted(glob.glob("results/*.csv")):
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
        if not rows or "feedback" not in rows[0]:
            skipped += 1          # very first runs did not record their settings
            continue
        levels = sorted({r["level"] for r in rows})
        if args.level and levels != [args.level]:
            continue
        if "tests_best" not in rows[0]:
            log = path[:-4] + ".log.md"
            if not os.path.exists(log):
                skipped += 1
                continue
            scores = rescore_from_log(log)
            for r in rows:
                r.setdefault("run", "1")
                first, best, total = scores.get((int(r["run"]), r["task"]), (0, 0, 0))
                r.update(tests_first=first, tests_best=best, tests_total=total)
        key = (rows[0]["model"], "+".join(levels), method_name(rows[0]))
        by_run = defaultdict(list)
        for r in rows:
            by_run[r.get("run", "1")].append(r)
        groups[key].extend(by_run.values())

    if not groups:
        print("No comparable results found. Run agent.py first.")
        return

    print(f"\n{'model':<11}{'tasks':<8}{'method':<50}{'runs':>5}{'tasks':>8}"
          f"{'first try':>11}{'best':>9}{'best range':>12}")
    print("-" * 114)
    for (model, levels, method), runs in sorted(groups.items(), key=lambda kv: kv[0]):
        n = len(runs)
        n_tasks = len(runs[0])
        total = sum(int(r["tests_total"]) for r in runs[0])
        tasks = sum(sum(r["status"] == "passed" for r in run) for run in runs) / n
        first = sum(sum(int(r["tests_first"]) for r in run) for run in runs) / n
        bests = [sum(int(r["tests_best"]) for r in run) for run in runs]
        print(f"{model:<11}{levels:<8}{method:<50}{n:>5}{f'{tasks:.1f}/{n_tasks}':>8}"
              f"{f'{first:.1f}/{total}':>11}{f'{sum(bests) / n:.1f}/{total}':>9}"
              f"{f'{min(bests)}-{max(bests)}':>12}")
    if skipped:
        print(f"\n(skipped {skipped} older result file(s) that did not record their settings)")
    print("\nfirst try = without self-checking.  best = with self-checking.  "
          "A small difference between methods with a wide 'best range' is probably luck.")


if __name__ == "__main__":
    main()
