"""
Self-Checking, Safe Coding Agent (v0.4)

Usage:
  python agent.py                     # run all tasks in tasks.py
  python agent.py --task roman        # run one task
  python agent.py --level hard        # run only hard tasks
  python agent.py --max-attempts 1    # self-checking OFF (for comparison)
  python agent.py --feedback simple   # raw Python errors only (for comparison)
  python agent.py --no-anti-stuck     # allow repeated code, temperature 0 (old behaviour)
  python agent.py --plan              # plan first (rules, worked examples, steps), then code
  python agent.py --list              # show task names

What it does:
  0. plan         -> (only with --plan) rules + worked examples + steps, no code yet
  1. write_code   -> the LLM writes Python code for a task
  2. check_repeat -> if the code is the same as an earlier failed attempt, ask for
                     a different approach (no test run wasted)
  3. check_safety -> blocks dangerous code (deleting files, running shell commands...)
  4. run_tests    -> runs the code + tests in a temporary folder with a time limit
  5. If tests fail, the error goes back to the LLM to fix (max 3 attempts)

Graph:
  START -> write_code -> check_repeat --(repeated)--> write_code (or END if out of attempts)
                              |
                            (new)
                              v
                         check_safety --(blocked)--> END
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
ANTI_STUCK = True            # stop the model repeating the same failed code (see check_repeat)
RETRY_TEMPERATURES = [0.0, 0.5, 0.8]   # temperature for attempt 1, 2, 3+ when ANTI_STUCK is on
PLAN_FIRST = False           # --plan: write rules + worked examples + steps BEFORE any code

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



def get_llm(attempt: int) -> ChatOllama:
    """Temperature 0 = same prompt always gives the same answer. On retries we raise it
    a little so the model can try something new instead of repeating itself."""
    if not ANTI_STUCK:
        return ChatOllama(model=MODEL, temperature=0)
    t = RETRY_TEMPERATURES[min(attempt, len(RETRY_TEMPERATURES)) - 1]
    return ChatOllama(model=MODEL, temperature=t)


# ---------------- State (the agent's memory) ----------------
class AgentState(TypedDict):
    task: str       # what the user wants
    tests: str      # assert statements that check the code
    code: str       # latest code written by the LLM
    feedback: str   # error message or safety reason from the last step
    attempts: int   # how many times the LLM has written code
    status: str     # "running" | "passed" | "blocked"
    history: list   # (code, result) for every attempt - saved to the log file
    repeats: int    # how many times the model returned code it had already tried
    plan: str       # latest plan (only with --plan)
    plans: list     # every plan, one per attempt - saved to the log file


# ---------------- Helpers ----------------
def extract_code(text: str) -> str:
    """Pull the code out of a ```python ... ``` block, if there is one."""
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


# ---------------- Nodes (the steps) ----------------
def make_plan(state: AgentState) -> dict:
    """Plan-first mode: before any code, the model writes the rules, works examples
    by hand, and lists the steps. On a retry it must find what was wrong in the PLAN,
    using the failing test as a worked example - not just patch the code."""
    prompt = (
        "You are planning a Python solution. Do NOT write any code yet.\n"
        f"Task: {state['task']}\n\n"
        "Write these three sections, short and exact:\n"
        "RULES: every rule in the task as a numbered list. Keep every exact detail "
        "(direction, order, when to leave something out, when to raise an error).\n"
        "EXAMPLES: work through 3 small inputs by hand, step by step, showing input -> output. "
        "Include at least one edge case. Check each output against the RULES.\n"
        "STEPS: the algorithm as numbered steps that follow the RULES.\n"
    )
    if state["feedback"]:
        prompt += (
            f"\nYour previous plan was:\n{state['plan']}\n\n"
            f"The code written from that plan failed:\n{state['feedback']}\n\n"
            "The failing case shows where your plan is wrong. Work through that exact input "
            "by hand using your RULES, find which rule or step is wrong or missing, and write "
            "a corrected plan. If the whole approach is wrong, choose a different approach.\n"
        )
    attempt = state["attempts"] + 1
    plan = get_llm(attempt).invoke(prompt).content.strip().replace("```", "\'\'\'")
    print(f"\n--- Attempt {attempt}: plan written ---")
    return {"plan": plan, "plans": state["plans"] + [plan]}


def write_code(state: AgentState) -> dict:
    prompt = (
        "You are a careful Python developer.\n"
        f"Task: {state['task']}\n\n"
        "Rules:\n"
        "- Return ONLY Python code inside one ```python block.\n"
        "- Do not write tests, do not use input(), do not touch files or the network.\n"
    )
    if PLAN_FIRST and state["plan"]:
        prompt += f"\nFollow this plan exactly:\n{state['plan']}\n"
    if state["feedback"]:
        if ANTI_STUCK and len(state["history"]) > 1:
            # remind the model of ALL earlier mistakes, not only the last one
            earlier = "\n".join(f"- attempt {i}: {res.strip().splitlines()[0][:200]}"
                                 for i, (_, res) in enumerate(state["history"][:-1], 1))
            prompt += f"\nEarlier attempts also failed:\n{earlier}\n"
        prompt += (
            "\nYour previous code failed.\n"
            f"Previous code:\n```python\n{state['code']}\n```\n"
            f"Error:\n{state['feedback']}\n"
            "Re-read the task rules carefully, find the real cause of the error, and fix the code.\n"
        )

    attempt = state["attempts"] + 1
    response = get_llm(attempt).invoke(prompt)
    print(f"\n--- Attempt {attempt}: code written ---")
    return {"code": extract_code(response.content), "attempts": attempt}


def check_repeat(state: AgentState) -> dict:
    """If the model returned code it already tried, don't waste a test run on it.
    Tell it clearly to try a different approach."""
    if not ANTI_STUCK:
        return {}
    for i, (old_code, old_result) in enumerate(state["history"], 1):
        if old_code.strip() == state["code"].strip():
            print(f"STUCK: same code as attempt {i} - asking for a different approach")
            fb = (f"You returned EXACTLY the same code as attempt {i}, which already failed with:\n"
                  f"{old_result}\n"
                  "Do not repeat it. Rethink the approach from the task rules and write a "
                  "DIFFERENT solution.")
            return {"status": "repeat", "feedback": fb, "repeats": state["repeats"] + 1,
                    "history": state["history"] + [(state["code"], "REPEATED attempt " + str(i))]}
    return {"status": "running"}


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
def next_try() -> str:
    """Where a retry goes: back to planning (plan-first mode) or straight to coding."""
    return "plan" if PLAN_FIRST else "write_code"


def after_repeat(state: AgentState) -> str:
    if state["status"] != "repeat":
        return "new"
    return "done" if state["attempts"] >= MAX_ATTEMPTS else next_try()


def after_safety(state: AgentState) -> str:
    return "blocked" if state["status"] == "blocked" else "safe"


def after_tests(state: AgentState) -> str:
    if state["status"] == "passed" or state["attempts"] >= MAX_ATTEMPTS:
        return "done"
    return next_try()


# ---------------- Build the graph ----------------
def build_agent():
    graph = StateGraph(AgentState)
    graph.add_node("plan", make_plan)
    graph.add_node("write_code", write_code)
    graph.add_node("check_repeat", check_repeat)
    graph.add_node("check_safety", check_safety)
    graph.add_node("run_tests", run_tests)

    graph.add_edge(START, next_try())
    graph.add_edge("plan", "write_code")
    graph.add_edge("write_code", "check_repeat")
    graph.add_conditional_edges("check_repeat", after_repeat,
                                {"new": "check_safety", "plan": "plan", "write_code": "write_code",
                                 "done": END})
    graph.add_conditional_edges("check_safety", after_safety, {"blocked": END, "safe": "run_tests"})
    graph.add_conditional_edges("run_tests", after_tests,
                                {"done": END, "plan": "plan", "write_code": "write_code"})
    return graph.compile()


# ---------------- Run the benchmark ----------------
def run_task(agent, item: dict) -> dict:
    """Run one task through the agent and return a result row."""
    print(f"\n================ {item['name']} ({item['level']}) ================")
    start = time.time()
    final = agent.invoke(
        {"task": item["task"], "tests": item["tests"], "code": "", "feedback": "",
         "attempts": 0, "status": "running", "history": [], "repeats": 0,
         "plan": "", "plans": []},
        {"recursion_limit": 50},
    )
    status = final["status"] if final["status"] in ("passed", "blocked") else "failed"
    return {
        "task": item["name"],
        "level": item["level"],
        "status": status,
        "attempts": final["attempts"],
        "repeats": final["repeats"],
        "seconds": round(time.time() - start, 1),
        "code": final["code"],
        "history": final["history"],
        "plans": final["plans"],
    }


def print_summary(rows: list[dict]) -> None:
    print("\n\n==================== SUMMARY ====================")
    print(f"{'task':<12}{'level':<8}{'status':<9}{'attempts':>9}{'repeats':>9}{'seconds':>9}")
    print("-" * 56)
    for r in rows:
        print(f"{r['task']:<12}{r['level']:<8}{r['status']:<9}{r['attempts']:>9}"
              f"{r['repeats']:>9}{r['seconds']:>9}")
    print("-" * 56)
    passed = sum(r["status"] == "passed" for r in rows)
    first_try = sum(r["status"] == "passed" and r["attempts"] == 1 for r in rows)
    print(f"Passed: {passed}/{len(rows)}   "
          f"(first try: {first_try}, fixed by retrying: {passed - first_try})   "
          f"Stuck repeats: {sum(r['repeats'] for r in rows)}")


def save_results(rows: list[dict]) -> str:
    """Save a CSV summary and a full log (every attempt's code + error) in results/."""
    os.makedirs("results", exist_ok=True)
    base = os.path.join("results", time.strftime("%Y%m%d-%H%M%S")
                        + f"-{MODEL.replace(':', '_')}-{FEEDBACK_MODE}-max{MAX_ATTEMPTS}"
                        + ("" if ANTI_STUCK else "-noantistuck") + ("-plan" if PLAN_FIRST else ""))
    fields = ["task", "level", "status", "attempts", "repeats", "seconds",
              "model", "feedback", "max_attempts", "anti_stuck", "plan_first"]
    with open(base + ".csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({**{k: r[k] for k in fields[:6]}, "model": MODEL,
                             "feedback": FEEDBACK_MODE, "max_attempts": MAX_ATTEMPTS,
                             "anti_stuck": ANTI_STUCK, "plan_first": PLAN_FIRST})
    with open(base + ".log.md", "w", encoding="utf-8") as f:
        f.write(f"# Run log\n\nModel: {MODEL} | feedback: {FEEDBACK_MODE} | max attempts: {MAX_ATTEMPTS}"
                f" | anti-stuck: {ANTI_STUCK} | plan-first: {PLAN_FIRST}\n")
        for r in rows:
            f.write(f"\n## {r['task']} ({r['level']}): {r['status']}\n")
            for i, (code, result) in enumerate(r["history"], 1):
                f.write(f"\n### Attempt {i}\n\n")
                if i <= len(r["plans"]):
                    f.write(f"Plan:\n\n```text\n{r['plans'][i - 1]}\n```\n\n")
                f.write(f"```python\n{code}\n```\n\nResult:\n\n```\n{result}\n```\n")
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
    parser.add_argument("--no-anti-stuck", action="store_true",
                        help="turn OFF repeat detection and retry temperatures (old behaviour)")
    parser.add_argument("--plan", action="store_true",
                        help="plan first: rules + worked examples + steps before writing code")
    parser.add_argument("--show-code", action="store_true", help="print the final code of each task")
    parser.add_argument("--list", action="store_true", help="list task names and exit")
    args = parser.parse_args()

    if args.list:
        for t in TASKS:
            print(f"{t['name']:<12}{t['level']}")
        sys.exit(0)

    MAX_ATTEMPTS = args.max_attempts
    FEEDBACK_MODE = args.feedback
    ANTI_STUCK = not args.no_anti_stuck
    PLAN_FIRST = args.plan
    selected = [t for t in TASKS
                if (not args.task or t["name"] == args.task)
                and (not args.level or t["level"] == args.level)]
    if not selected:
        sys.exit(f"No task matched. Use --list to see task names.")

    print(f"Model: {MODEL}   Max attempts: {MAX_ATTEMPTS}   Feedback: {FEEDBACK_MODE}   "
          f"Anti-stuck: {'on' if ANTI_STUCK else 'off'}   Plan-first: {'on' if PLAN_FIRST else 'off'}   "
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
