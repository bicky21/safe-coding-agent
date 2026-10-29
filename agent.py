"""
Self-Checking, Safe Coding Agent - starter version (v0.1)

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

import os
import re
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
            return {"status": "blocked", "feedback": f"Blocked: {reason} ({pattern})"}
    print("Safety check passed")
    return {"status": "running"}


def run_tests(state: AgentState) -> dict:
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "solution.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(state["code"] + "\n\n# ---- tests ----\n" + state["tests"] + "\n")
        try:
            result = subprocess.run(
                [sys.executable, path],
                capture_output=True,
                text=True,
                timeout=TEST_TIMEOUT_SECONDS,
                cwd=folder,
            )
        except subprocess.TimeoutExpired:
            print("Tests timed out")
            return {"feedback": f"Timed out after {TEST_TIMEOUT_SECONDS}s (infinite loop?)"}

    if result.returncode == 0:
        print("All tests passed")
        return {"status": "passed", "feedback": ""}

    print("Tests failed")
    return {"feedback": (result.stderr or result.stdout)[-2000:]}


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


# ---------------- Try it ----------------
if __name__ == "__main__":
    agent = build_agent()

    task = (
        "Write a function is_palindrome(s: str) -> bool that returns True if s is a "
        "palindrome, ignoring case, spaces and punctuation."
    )
    tests = """
assert is_palindrome("A man, a plan, a canal: Panama") is True
assert is_palindrome("racecar") is True
assert is_palindrome("hello") is False
assert is_palindrome("") is True
print("tests ok")
"""

    final = agent.invoke(
        {"task": task, "tests": tests, "code": "", "feedback": "", "attempts": 0, "status": "running"}
    )

    print("\n========== RESULT ==========")
    print("Status  :", final["status"] if final["status"] != "running" else "failed")
    print("Attempts:", final["attempts"])
    print("Code:\n" + final["code"])
