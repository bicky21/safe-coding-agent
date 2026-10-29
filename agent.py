"""
Self-Checking, Safe Coding Agent (v0.2)

Usage:
  python agent.py                     # run all tasks in tasks.py
  python agent.py --task roman        # run one task
  python agent.py --level hard        # run only hard tasks
  python agent.py --max-attempts 1    # self-checking OFF (for comparison)
  python agent.py --feedback simple   # raw Python errors only (for comparison)
  python agent.py --list              # show task names

What it does:
  1. write_code   -> the LLM writes Python code for a task
  2. check_safety -> blocks dangerous code (deleting files, running shell commands...)
  3. run_tests    -> runs the code + tests in a temporary folder with a time limit
  4. If tests fail, the error goes back to the LLM to fix (max 3 attempts)

Graph:
  START -> write_code -> check_safety --(blocked)--> END
                              |
                           (safe)
                              v
                          run_tests --(passed or out of attempts)--> END
                              |
                           (failed)
                              v
                          write_code  (try again with the error message)
"""

import argparse
import csv
import os
import re
import time
import subprocess
import sys
import tempfile
from typing import TypedDict

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

# ---------------- Settings ----------------
# Use whichever Gemma model you pulled with Ollama, e.g. `ollama pull gemma3:4b`
MODEL = os.environ.get("AGENT_MODEL", "gemma3:4b")
MAX_ATTEMPTS = 3
TEST_TIMEOUT_SECONDS = 10
FEEDBACK_MODE = "detailed"   # "detailed" (which test, got vs expected) or "simple" (raw error)

# Very simple safety rules (v0.1). You will improve these later.
BLOCKED_PATTERNS = {
    r"\bos\.system\b": "running shell commands",
    r"\bsubprocess\b": "running shell commands",
    r"\bshutil\.rmtree\b": "deleting folders",
    r"\bos\.(remove|unlink|rmdir)\b": "deleting files",
    r"rm\s+-rf": "deleting files",
    r"\beval\s*\(": "running hidden code",
    r"\bexec\s*\(": "running hidden code",
    r"__import__": "hidden imports",
    r"\b(socket|requests|urllib)\b": "network access",
}

llm = ChatOllama(model=MODEL, temperature=0)


# ---------------- State (the agent's memory) ----------------
class AgentState(TypedDict):
    task: str       # what the user wants
    tests: str      # assert statements that check the code
    code: str       # latest code written by the LLM
    feedback: str   # error message or safety reason from the last step
    attempts: int   # how many times the LLM has written code
    status: str     # "running" | "passed" | "blocked"
    history: list   # (code, result) for every attempt - saved to the log file


# ---------------- Helpers ----------------
def extract_code(text: str) -> str:
    """Pull the code out of a ```python ... ``` block, if there is one."""
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


# ---------------- Nodes (the steps) ----------------
def write_code(state: AgentState) -> dict:
    prompt = (
        "You are a careful Python developer.\n"
        f"Task: {state['task']}\n\n"
        "Rules:\n"
        "- Return ONLY Python code inside one ```python block.\n"
        "- Do not write tests, do not use input(), do not touch files or the network.\n"
    )
    if state["feedback"]:
        prompt += (
            "\nYour previous code failed.\n"
            f"Previous code:\n```python\n{state['code']}\n```\n"
            f"Error:\n{state['feedback']}\n"
            "Fix the code.\n"
        )

    response = llm.invoke(prompt)
    attempt = state["attempts"] + 1
    print(f"\n--- Attempt {attempt}: code written ---")
    return {"code": extract_code(response.content), "attempts": attempt}


def check_safety(state: AgentState) -> dict:
    for pattern, reason in BLOCKED_PATTERNS.items():
        if re.search(pattern, state["code"]):
            print(f"BLOCKED: code tried {reason}")
            fb = f"Blocked: {reason} ({pattern})"
            return {"status": "blocked", "feedback": fb,
                    "history": state["history"] + [(state["code"], fb)]}
    print("Safety check passed")
    return {"status": "running"}


# Test runner used in "detailed" feedback mode.
# It rewrites every `assert a == b` / `assert a is b` in the tests so that, when
# one fails, the error says WHICH test failed, what the code returned, and what
# was expected - instead of a bare "AssertionError".
HARNESS = r'''
import ast, sys, traceback

def _trace():
    """Error trace without this runner's own lines (they would only confuse the model)."""
    etype, e, tb = sys.exc_info()
    frames = [f for f in traceback.extract_tb(tb) if not f.filename.endswith("harness.py")]
    return "".join(traceback.format_list(frames[-3:]) + traceback.format_exception_only(etype, e))

def _check(got, expected, op, src):
    ok = (got is expected) if op == "is" else (got == expected)
    if not ok:
        raise AssertionError(
            f"Test failed: {src}\n  your code returned: {got!r}\n  expected:           {expected!r}")

class _Rewrite(ast.NodeTransformer):
    def visit_Assert(self, node):
        t = node.test
        if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], (ast.Eq, ast.Is)):
            op = "is" if isinstance(t.ops[0], ast.Is) else "=="
            call = ast.Call(ast.Name("_check", ast.Load()),
                            [t.left, t.comparators[0], ast.Constant(op), ast.Constant(ast.unparse(node))], [])
            return ast.copy_location(ast.Expr(call), node)
        return node

code = open("solution.py", encoding="utf-8").read()
tests = open("tests.py", encoding="utf-8").read()
ns = {"_check": _check}
try:
    exec(compile(code, "solution.py", "exec"), ns)
except Exception:
    print("Your code crashed before the tests ran:\n" + _trace(), file=sys.stderr)
    sys.exit(1)

tree = ast.fix_missing_locations(_Rewrite().visit(ast.parse(tests)))
try:
    exec(compile(tree, "tests.py", "exec"), ns)
except AssertionError as e:
    if str(e).startswith("Test failed"):
        print(e, file=sys.stderr)
    else:
        line = traceback.extract_tb(e.__traceback__)[-1]
        print(f"Test failed at tests.py line {line.lineno}: {line.line}\n{e}", file=sys.stderr)
    sys.exit(1)
except Exception:
    test_lines = [f for f in traceback.extract_tb(sys.exc_info()[2]) if f.filename == "tests.py"]
    where = ""
    if test_lines:
        line = test_lines[-1].line
        where = f"while running test: {line}\n"
        # show the values of loop variables used on that line, e.g. args = (2026, 2, 0, 5)
        try:
            names = {n.id for n in ast.walk(ast.parse(line.strip())) if isinstance(n, ast.Name)}
        except SyntaxError:
            names = set()
        for n in sorted(names):
            v = ns.get(n)
            if isinstance(v, (int, float, str, tuple, list, dict)):
                where += f"  where {n} = {v!r}\n"
    print(f"Your code raised an error {where}" + _trace(), file=sys.stderr)
    sys.exit(1)
'''


def run_tests(state: AgentState) -> dict:
    with tempfile.TemporaryDirectory() as folder:
        if FEEDBACK_MODE == "detailed":
            for name, text in [("solution.py", state["code"]), ("tests.py", state["tests"]),
                               ("harness.py", HARNESS)]:
                with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
                    f.write(text + "\n")
            script = "harness.py"
        else:  # "simple": code + tests in one file, raw Python error
            with open(os.path.join(folder, "solution.py"), "w", encoding="utf-8") as f:
                f.write(state["code"] + "\n\n# ---- tests ----\n" + state["tests"] + "\n")
            script = "solution.py"
        try:
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True,
                text=True,
                timeout=TEST_TIMEOUT_SECONDS,
                cwd=folder,
            )
        except subprocess.TimeoutExpired:
            print("Tests timed out")
            fb = f"Timed out after {TEST_TIMEOUT_SECONDS}s (infinite loop?)"
            return {"feedback": fb, "history": state["history"] + [(state["code"], fb)]}

    if result.returncode == 0:
        print("All tests passed")
        return {"status": "passed", "feedback": "",
                "history": state["history"] + [(state["code"], "PASSED")]}

    print("Tests failed")
    fb = (result.stderr or result.stdout)[-2000:]
    return {"feedback": fb, "history": state["history"] + [(state["code"], fb)]}


# ---------------- Routing (which step comes next) ----------------
def after_safety(state: AgentState) -> str:
    return "blocked" if state["status"] == "blocked" else "safe"


def after_tests(state: AgentState) -> str:
    if state["status"] == "passed" or state["attempts"] >= MAX_ATTEMPTS:
        return "done"
    return "retry"


# ---------------- Build the graph ----------------
def build_agent():
    graph = StateGraph(AgentState)
    graph.add_node("write_code", write_code)
    graph.add_node("check_safety", check_safety)
    graph.add_node("run_tests", run_tests)

    graph.add_edge(START, "write_code")
    graph.add_edge("write_code", "check_safety")
    graph.add_conditional_edges("check_safety", after_safety, {"blocked": END, "safe": "run_tests"})
    graph.add_conditional_edges("run_tests", after_tests, {"done": END, "retry": "write_code"})
    return graph.compile()


# ---------------- Run the benchmark ----------------
def run_task(agent, item: dict) -> dict:
    """Run one task through the agent and return a result row."""
    print(f"\n================ {item['name']} ({item['level']}) ================")
    start = time.time()
    final = agent.invoke(
        {"task": item["task"], "tests": item["tests"], "code": "", "feedback": "",
         "attempts": 0, "status": "running", "history": []},
        {"recursion_limit": 50},
    )
    status = final["status"] if final["status"] != "running" else "failed"
    return {
        "task": item["name"],
        "level": item["level"],
        "status": status,
        "attempts": final["attempts"],
        "seconds": round(time.time() - start, 1),
        "code": final["code"],
        "history": final["history"],
    }


def print_summary(rows: list[dict]) -> None:
    print("\n\n==================== SUMMARY ====================")
    print(f"{'task':<12}{'level':<8}{'status':<9}{'attempts':>9}{'seconds':>9}")
    print("-" * 47)
    for r in rows:
        print(f"{r['task']:<12}{r['level']:<8}{r['status']:<9}{r['attempts']:>9}{r['seconds']:>9}")
    print("-" * 47)
    passed = sum(r["status"] == "passed" for r in rows)
    first_try = sum(r["status"] == "passed" and r["attempts"] == 1 for r in rows)
    print(f"Passed: {passed}/{len(rows)}   "
          f"(first try: {first_try}, fixed by retrying: {passed - first_try})")


def save_results(rows: list[dict]) -> str:
    """Save a CSV summary and a full log (every attempt's code + error) in results/."""
    os.makedirs("results", exist_ok=True)
    base = os.path.join("results", time.strftime("%Y%m%d-%H%M%S")
                        + f"-{MODEL.replace(':', '_')}-{FEEDBACK_MODE}-max{MAX_ATTEMPTS}")
    fields = ["task", "level", "status", "attempts", "seconds", "model", "feedback", "max_attempts"]
    with open(base + ".csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({**{k: r[k] for k in fields[:5]}, "model": MODEL,
                             "feedback": FEEDBACK_MODE, "max_attempts": MAX_ATTEMPTS})
    with open(base + ".log.md", "w", encoding="utf-8") as f:
        f.write(f"# Run log\n\nModel: {MODEL} | feedback: {FEEDBACK_MODE} | max attempts: {MAX_ATTEMPTS}\n")
        for r in rows:
            f.write(f"\n## {r['task']} ({r['level']}): {r['status']}\n")
            for i, (code, result) in enumerate(r["history"], 1):
                f.write(f"\n### Attempt {i}\n\n```python\n{code}\n```\n\nResult:\n\n```\n{result}\n```\n")
    return base + ".csv"


if __name__ == "__main__":
    from tasks import TASKS

    parser = argparse.ArgumentParser(description="Self-checking safe coding agent")
    parser.add_argument("--task", help="run only this task (e.g. roman). Default: all tasks")
    parser.add_argument("--level", choices=["easy", "medium", "hard", "tricky"], help="run only this level")
    parser.add_argument("--max-attempts", type=int, default=MAX_ATTEMPTS,
                        help="tries per task (use 1 to switch self-checking off)")
    parser.add_argument("--feedback", choices=["detailed", "simple"], default=FEEDBACK_MODE,
                        help="detailed = which test failed + got vs expected; simple = raw error")
    parser.add_argument("--show-code", action="store_true", help="print the final code of each task")
    parser.add_argument("--list", action="store_true", help="list task names and exit")
    args = parser.parse_args()

    if args.list:
        for t in TASKS:
            print(f"{t['name']:<12}{t['level']}")
        sys.exit(0)

    MAX_ATTEMPTS = args.max_attempts
    FEEDBACK_MODE = args.feedback
    selected = [t for t in TASKS
                if (not args.task or t["name"] == args.task)
                and (not args.level or t["level"] == args.level)]
    if not selected:
        sys.exit(f"No task matched. Use --list to see task names.")

    print(f"Model: {MODEL}   Max attempts: {MAX_ATTEMPTS}   Feedback: {FEEDBACK_MODE}   "
          f"Tasks: {len(selected)}")
    agent = build_agent()
    rows = [run_task(agent, t) for t in selected]

    if args.show_code:
        for r in rows:
            print(f"\n----- code for {r['task']} ({r['status']}) -----\n{r['code']}")

    print_summary(rows)
    csv_path = save_results(rows)
    print(f"Saved: {csv_path}")
    print(f"Log:   {csv_path[:-4]}.log.md   (every attempt's code and error)")
