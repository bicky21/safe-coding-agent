"""
Analyze run logs in results/.

For every task in every log it shows:
  - how many attempts were made
  - which attempts were EXACT copies of an earlier attempt ("stuck")
  - the first line of the error for each attempt

Usage:
  python analyze.py                      # all logs in results/
  python analyze.py results/<file>.log.md
"""

import glob
import re
import sys


def analyze(path: str) -> tuple[int, int]:
    text = open(path, encoding="utf-8").read()
    header = text.split("\n")[2] if "\n" in text else ""
    print(f"\n# {path}\n  {header}")
    total_retries = total_stuck = 0

    for section in re.split(r"\n## ", text)[1:]:
        name = section.split("\n")[0]
        attempts = re.findall(
            r"### Attempt \d+\n\n```python\n(.*?)\n```\n\nResult:\n\n```\n(.*?)\n```", section, re.S)
        seen = []
        stuck = []
        for i, (code, _) in enumerate(attempts, 1):
            if code.strip() in seen:
                stuck.append(i)
            seen.append(code.strip())
        total_retries += max(len(attempts) - 1, 0)
        total_stuck += len(stuck)

        print(f"\n  {name}")
        for i, (_, result) in enumerate(attempts, 1):
            first = (result.strip().splitlines() or [""])[0][:90]
            mark = "  <- SAME CODE AS BEFORE" if i in stuck else ""
            print(f"    attempt {i}: {first}{mark}")

    if total_retries:
        print(f"\n  Retries: {total_retries}   Stuck (identical code): {total_stuck} "
              f"({100 * total_stuck // total_retries}%)")
    return total_retries, total_stuck


if __name__ == "__main__":
    paths = sys.argv[1:] or sorted(glob.glob("results/*.log.md"))
    if not paths:
        sys.exit("No log files found in results/. Run agent.py first.")
    for p in paths:
        analyze(p)
