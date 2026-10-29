"""The agent: a LangGraph loop that plans, writes, checks, tests and fixes code.

    START -> [plan] -> write_code -> check_repeat -> check_safety -> run_tests -> END
                ^           |              |              |             |
                |           +-- invalid ---+-- repeat ----+-- blocked --+-- failed
                +------------------------- retry (until max_attempts) --+

Every attempt is recorded (plan, files, test result) so runs can be analysed later.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field, replace
from typing import Any, Callable, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from . import prompts
from .models import REPLY_RESERVE, ModelSpec, context_for, invoke_with_retry, make_model
from .safety import check_files
from .sandbox import RunResult
from .tasks import Task


@dataclass
class Settings:
    model: ModelSpec
    max_attempts: int = 3                 # real attempts (tested or blocked); invalid answers and
                                          # repeats don't count, up to 2x this many model calls
    feedback: str = "detailed"            # detailed | simple
    anti_stuck: bool = True               # catch repeated code, raise temperature on retries
    plan_first: bool = False              # write a plan before each code attempt
    safety: str | None = None             # override the task's level: standard | strict | off
    temperatures: tuple[float, ...] = (0.0, 0.5, 0.8)
    context_chars: int | None = None      # how much existing code may go into one prompt
                                          # (default: fits the Ollama window, else 120,000)
    timeout: int | None = None            # override the task's test timeout

    def temperature(self, attempt: int) -> float:
        if not self.anti_stuck:
            return 0.0
        return self.temperatures[min(attempt, len(self.temperatures)) - 1]

    @property
    def code_budget(self) -> int:
        if self.context_chars:
            return self.context_chars
        if self.model.provider == "ollama":
            limit = int(os.environ.get("SCA_OLLAMA_MAX_CTX", "32768"))
            # leave ~4000 tokens for the task, instructions, test feedback and plan
            return max((limit - REPLY_RESERVE - 4000) * 3, 8000)
        return 120_000

    def describe(self) -> dict[str, Any]:
        return {"model": self.model.label, "max_attempts": self.max_attempts, "feedback": self.feedback,
                "anti_stuck": self.anti_stuck, "plan_first": self.plan_first,
                "safety": self.safety or "task default"}


@dataclass
class Attempt:
    number: int
    status: str                      # passed | failed | blocked | repeat | invalid | error
    files: dict[str, str]
    feedback: str
    passed: int = 0
    total: int = 0
    plan: str = ""
    seconds: float = 0.0
    violations: list[str] = field(default_factory=list)
    reply: str = ""                  # the model's raw answer (kept for debugging)
    failure_signature: tuple = ()    # which tests failed and how (to spot changes that fix nothing)
    tested_files: dict[str, str] = field(default_factory=dict)   # every model file in the tested workspace

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


REAL = ("passed", "failed", "blocked")      # attempt kinds that use up one of max_attempts
REPLY_LIMIT = 20_000


class State(TypedDict, total=False):
    files: dict[str, str]        # the model's current version of every file it wrote
    new_files: dict[str, str]    # files from the latest reply
    reply: str                   # the latest raw reply
    plan: str
    feedback: str
    attempts: list[Attempt]
    status: str
    started: float


Event = Callable[[str], None]


class CodingAgent:
    def __init__(self, task: Task, settings: Settings, runner, on_event: Event | None = None):
        self.task, self.s, self.runner = task, settings, runner
        self.say = on_event or (lambda msg: None)
        self._warned_ctx = False
        self.graph = self._build()

    # ------------------------------------------------------------ helpers
    def _ask(self, system: str, prompt: str, attempt: int) -> str:
        spec = self.s.model
        if spec.provider == "ollama":
            num_ctx, fits = context_for(len(system) + len(prompt))
            if not fits and not self._warned_ctx:
                self._warned_ctx = True
                self.say(f"WARNING: prompt (~{len(prompt) // 3} tokens) is bigger than the Ollama context "
                         f"limit ({num_ctx}); Ollama will cut it. Raise SCA_OLLAMA_MAX_CTX or lower --context-chars")
            spec = replace(spec, num_ctx=num_ctx)
        model = make_model(spec, self.s.temperature(attempt))
        return invoke_with_retry(model, [SystemMessage(system), HumanMessage(prompt)])

    def _n(self, state: State) -> int:
        return len(state.get("attempts", []))

    def _record(self, state: State, status: str, feedback: str, **extra) -> dict:
        attempt = Attempt(number=self._n(state) + 1, status=status,
                          files=dict(state.get("new_files", {})), feedback=feedback,
                          plan=state.get("plan", "") if self.s.plan_first else "",
                          seconds=round(time.time() - state.get("started", time.time()), 1),
                          reply=state.get("reply", "")[:REPLY_LIMIT], **extra)
        return {"attempts": state.get("attempts", []) + [attempt], "feedback": feedback,
                "status": status, "started": time.time()}

    def _earlier(self, state: State) -> list[str]:
        if not self.s.anti_stuck:
            return []
        return [f"attempt {a.number}: {prompts.first_line(a.feedback)}" for a in state.get("attempts", [])[:-1]]

    # ------------------------------------------------------------ nodes
    def plan(self, state: State) -> dict:
        n = self._n(state) + 1
        self.say(f"attempt {n}: planning")
        text = self._ask(prompts.PLAN_SYSTEM, prompts.plan_prompt(
            self.task, state.get("files", {}), state.get("plan", ""), state.get("feedback", ""),
            self.s.code_budget), n)
        return {"plan": text.strip()}

    def write_code(self, state: State) -> dict:
        n = self._n(state) + 1
        self.say(f"attempt {n}: writing code")
        reply = self._ask(prompts.SYSTEM, prompts.code_prompt(
            self.task, state.get("files", {}), state.get("plan", "") if self.s.plan_first else "",
            state.get("feedback", ""), self._earlier(state), self.s.code_budget), n)
        files, problems = prompts.parse_files(reply, self.task)
        if problems and not files:
            fb = ("Your answer could not be used: " + "; ".join(problems) + ".\n\n" + prompts.OUTPUT_FORMAT)
            self.say(f"attempt {n}: invalid answer ({'; '.join(problems)[:80]}) - not counted, retrying")
            return {"new_files": {}, "reply": reply,
                    **self._record({**state, "new_files": {}, "reply": reply}, "invalid", fb)}
        if problems:
            self.say(f"attempt {n}: ignored {len(problems)} file(s): {'; '.join(problems)[:80]}")
        return {"new_files": files, "reply": reply, "status": "written"}

    def check_repeat(self, state: State) -> dict:
        if not self.s.anti_stuck:
            return {}
        merged = {**state.get("files", {}), **state["new_files"]}
        for a in state.get("attempts", []):
            if a.status in ("invalid",):
                continue
            if a.files and {**state.get("files", {}), **a.files} == merged and a.files == state["new_files"]:
                self.say(f"attempt {self._n(state) + 1}: same code as attempt {a.number} - not counted, "
                         "starting over from the original code")
                fb = (f"You returned EXACTLY the same code as attempt {a.number}, which already failed:\n"
                      f"{a.feedback}\n\nDo not repeat it. STARTING OVER: the project files above are the ORIGINAL "
                      "starter code again, without your earlier changes. Write the solution again from scratch, "
                      "with a DIFFERENT approach, and make sure it fixes the failures listed.")
                # fresh start: the model's failed versions are no longer shown, so it can't copy them again
                return {**self._record(state, "repeat", fb, passed=a.passed, total=a.total), "files": {}}
        return {}

    def check_safety(self, state: State) -> dict:
        level = self.s.safety or self.task.safety
        found = check_files(state["new_files"], self.task.allow_imports, level)
        if not found:
            return {}
        lines = [str(v) for v in found]
        self.say(f"attempt {self._n(state) + 1}: BLOCKED by safety check ({lines[0][:70]})")
        fb = ("Your code was blocked by the safety check and was NOT run:\n" + "\n".join(lines[:20]) +
              "\n\nSolve the task without these operations.")
        return self._record(state, "blocked", fb, total=self.task.count_tests(), violations=lines)

    def run_tests(self, state: State) -> dict:
        files = {**state.get("files", {}), **state["new_files"]}
        n = self._n(state) + 1
        res: RunResult = self.runner.run(self.task, files, self.s.timeout)
        status = "passed" if res.all_passed else "failed"
        self.say(f"attempt {n}: {res.passed}/{res.total} tests passed"
                 + (" (timeout)" if res.timed_out else "") + (" (import failed)" if res.collection_error else ""))
        fb = "" if status == "passed" else prompts.feedback_text(res, self.s.feedback)
        if status == "failed" and self.s.anti_stuck:
            same = self._same_failures_as(state, res)
            if same:
                self.say(f"attempt {n}: no progress - same failures as attempt {same.number}")
                fb = (f"Your change did NOT fix anything: the same {len(res.failures)} test(s) fail in exactly the "
                      f"same way as in attempt {same.number}. Changing code that is not on the failing path does "
                      "not help. Read each error below, find the exact line it points to, and change THAT logic.\n\n"
                      + fb)
        out = self._record(state, status, fb or "all tests passed", passed=res.passed, total=res.total,
                           failure_signature=_failure_signature(res), tested_files=files)
        out["files"] = files
        return out

    def _same_failures_as(self, state: State, res: RunResult) -> "Attempt | None":
        """The latest earlier tested attempt that failed in exactly the same way, if any."""
        sig = _failure_signature(res)
        if not sig:
            return None
        for a in reversed(state.get("attempts", [])):
            if a.status == "failed":
                return a if a.failure_signature == sig else None
        return None

    # ------------------------------------------------------------ routing
    def _retry_target(self) -> str:
        return "plan" if self.s.plan_first else "write_code"

    def _after_attempt(self, state: State) -> str:
        attempts = state.get("attempts", [])
        real = sum(a.status in REAL for a in attempts)
        if state.get("status") == "passed" or real >= self.s.max_attempts \
                or len(attempts) >= 2 * self.s.max_attempts:
            return "done"
        last = [a.status for a in attempts[-3:]]
        if last[-2:] == ["repeat", "repeat"] or (len(last) == 3 and set(last) <= {"repeat", "invalid"}):
            # even a fresh start didn't help: more tries would only cost time (and heat)
            self.say("stopping early: the model keeps repeating itself or giving unusable answers")
            return "done"
        return "retry"

    def _after_write(self, state: State) -> str:
        return self._after_attempt(state) if state.get("status") == "invalid" else "ok"

    def _after_check(self, state: State) -> str:
        if state.get("status") in ("repeat", "blocked"):
            return self._after_attempt(state)
        return "ok"

    def _build(self):
        g = StateGraph(State)
        g.add_node("plan", self.plan)
        g.add_node("write_code", self.write_code)
        g.add_node("check_repeat", self.check_repeat)
        g.add_node("check_safety", self.check_safety)
        g.add_node("run_tests", self.run_tests)
        retry = self._retry_target()
        g.add_edge(START, retry)
        g.add_edge("plan", "write_code")
        g.add_conditional_edges("write_code", self._after_write,
                                {"ok": "check_repeat", "retry": retry, "done": END})
        g.add_conditional_edges("check_repeat", self._after_check,
                                {"ok": "check_safety", "retry": retry, "done": END})
        g.add_conditional_edges("check_safety", self._after_check,
                                {"ok": "run_tests", "retry": retry, "done": END})
        g.add_conditional_edges("run_tests", self._after_attempt, {"retry": retry, "done": END})
        return g.compile()

    # ------------------------------------------------------------ public
    def run(self) -> "TaskResult":
        start = time.time()
        state: State = self.graph.invoke(
            {"files": {}, "new_files": {}, "reply": "", "plan": "", "feedback": "", "attempts": [], "status": "",
             "started": start},
            {"recursion_limit": 20 * self.s.max_attempts + 10})
        return TaskResult.from_attempts(self.task, state.get("attempts", []), time.time() - start)


@dataclass
class TaskResult:
    task: str
    level: str
    status: str
    attempts: list[Attempt]
    seconds: float
    first_passed: int
    best_passed: int
    total: int
    best_files: dict[str, str]

    @classmethod
    def from_attempts(cls, task: Task, attempts: list[Attempt], seconds: float) -> "TaskResult":
        total = max((a.total for a in attempts), default=0) or task.count_tests()
        tested = [a for a in attempts if a.status in ("passed", "failed")]
        best = max(tested, key=lambda a: (a.passed, a.number), default=None)
        if any(a.status == "passed" for a in attempts):
            status = "passed"
        elif attempts and attempts[-1].status == "blocked":
            status = "blocked"
        else:
            status = "failed"
        first = attempts[0].passed if attempts else 0
        return cls(task.name, task.level, status, attempts, round(seconds, 1), first,
                   best.passed if best else 0, total, dict(best.tested_files) if best else {})

    @property
    def repeats(self) -> int:
        return sum(a.status == "repeat" for a in self.attempts)

    @property
    def blocked(self) -> int:
        return sum(a.status == "blocked" for a in self.attempts)


def _failure_signature(res: RunResult) -> tuple:
    """Failing test names + the first line of each error, ignoring file paths/line numbers."""
    def norm(msg: str) -> str:
        first = (msg or "").strip().splitlines()[0] if msg and msg.strip() else ""
        return re.sub(r"(line \d+|:\d+:|/tmp/\S+)", "", first)[:200]
    return tuple(sorted((f.name, norm(f.message)) for f in res.failures))
