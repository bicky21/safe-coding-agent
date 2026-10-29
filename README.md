# Safe Coding Agent

A self-checking, sandboxed coding agent built with [LangGraph](https://github.com/langchain-ai/langgraph).

You describe what to build and write **pytest tests** that define "correct". The agent plans,
writes the code (one or many files, on top of your existing code if you want), checks it for
dangerous operations, runs your tests in a sandbox, reads the failures, and fixes its own
code until the tests pass or it runs out of attempts.

It works with **local models** (Ollama), **OpenAI-compatible APIs** (OpenAI, Groq,
OpenRouter, Gemini, LM Studio, vLLM...) and **Anthropic Claude**.

```
START -> [plan] -> write code -> same as before? -> safety check -> run tests (sandbox) -> done
            ^                          |                 |                  |
            +------- retry with the reason (repeat / blocked / failing tests) -----+
```

## Install

Python 3.10+.

```bash
git clone https://github.com/bicky21/safe-coding-agent.git
cd safe-coding-agent
python3 -m venv venv && source venv/bin/activate
pip install -e ".[ollama]"        # or [openai], [anthropic], or [all]
```

## Quick start

```bash
# 1. a model (local and free)
ollama pull gemma3:4b

# 2. try the built-in multi-file example
sca run examples/todo-project

# 3. or make your own task
sca new-task my-task
#    edit my-task/task.yaml and my-task/tests/, then:
sca run my-task --out my-task/solution
```

Every run is saved in `sca-runs/` with a readable log of every attempt and the **best code
it produced** (`solutions/`). `--out DIR` also copies the best code wherever you want.

## Choosing a model

```bash
sca run my-task --model ollama:gemma3:4b                       # local (default)
sca run my-task --model ollama:qwen2.5-coder:14b

export ANTHROPIC_API_KEY=sk-ant-...
sca run my-task --model anthropic:claude-sonnet-5-5

export OPENAI_API_KEY=sk-...
sca run my-task --model openai:gpt-4o-mini

export GROQ_API_KEY=gsk_...                                    # any OpenAI-compatible API
sca run my-task --model openai:llama-3.3-70b-versatile \
    --base-url https://api.groq.com/openai/v1 --api-key-env GROQ_API_KEY

sca run my-task --model openai:local-model --base-url http://localhost:1234/v1   # LM Studio
```

Set a default with `export SCA_MODEL=anthropic:claude-sonnet-5-5`. Remote Ollama:
`--base-url http://host:11434` (or `OLLAMA_HOST`). Bigger Ollama context window:
`export SCA_OLLAMA_NUM_CTX=32768`.

## Writing a task

A task is a folder:

```
my-task/
  task.yaml       what to build + settings
  tests/          pytest tests that decide if the code is correct (the model can't change them)
  starter/        optional: existing code the model works on (copied into the sandbox)
```

`task.yaml`:

```yaml
name: my-task
prompt: |
  Add a `search(query)` method to `library/catalog.py` that ...
files: [library/catalog.py, library/search.py]   # files the model is expected to write
timeout: 60             # seconds for one test run
show_tests: false       # true = the model can read the tests (like test-driven development)
safety: standard        # standard | strict | off
allow_imports: []       # modules your task really needs, e.g. [subprocess]
level: custom           # any tag; filter with: sca bench --level ...
```

The prompt can also live in a `task.md` file. See [`examples/todo-project`](examples/todo-project)
for a complete multi-file task with starter code.

**Bigger code bases:** everything in `starter/` is shown to the model, up to
`--context-chars` (default 120,000 characters, about 30k tokens); files beyond that are listed
by name only. Put the files that matter in `starter/`, and use a model with a large context
window for big projects.

## Safety

Model-written code is treated as untrusted. There are two layers:

**1. Static safety check (before any code runs).** The agent reads the code's structure
(Python AST, not text matching, so tricks like `getattr(os, "sys" + "tem")` are caught) and
blocks it before it is executed. The model is told why and tries again.

| Level | Blocks |
|-------|--------|
| `standard` (default) | network, starting programs (`subprocess`, `os.system`, `os.exec*`...), deleting/moving files, `eval`/`exec`/`importlib`, sandbox-escape tricks (`__subclasses__`, `__globals__`, frame objects...) |
| `strict` | all of the above, plus writing files, `sys`/`pathlib`/`inspect`, computed `getattr`, `os.environ`, object internals like `__dict__` |
| `off` | nothing (rely on the sandbox only) |

Check your own files: `sca check myfile.py --safety strict`.

**2. Sandbox (where the tests run).**

| Runner | Isolation |
|--------|-----------|
| `docker` (**recommended for untrusted models**) | throw-away container: no network, read-only file system, no Linux capabilities, never root, memory/CPU/process limits |
| `local` | subprocess in a temp folder, clean environment (your API keys are *not* passed in), killed on timeout, CPU/file-size limits. Runs as your user: fine for your own experiments, **not** strong isolation |

```bash
sca sandbox build           # once (add packages your tasks need: --package numpy)
sca sandbox status
sca run my-task --runner docker
```

The default `--runner auto` uses Docker when the image is built, and otherwise falls back to
`local` with a warning.

A static check can never be perfect, which is why the sandbox exists. If you find a way
past either layer, please open an issue.

## Benchmarking models and methods

A built-in benchmark of 13 tasks is included: 7 well-known problems (palindrome, LCS,
Dijkstra, LRU cache...) and 6 **tricky** tasks with unusual exact rules that models can't
answer from memory.

```bash
sca list                                          # built-in tasks
sca bench --level tricky --runs 3                 # default method
sca bench --level tricky --runs 3 --plan          # plan-first
sca bench --level tricky --runs 3 --feedback simple
sca bench --suite path/to/my-tasks --jobs 4       # your own suite, 4 tasks in parallel (API models)
sca compare                                       # every method side by side
```

Each result reports tests passed on the **first try** (= without self-checking) and by the
**best attempt** (= with self-checking), so partial progress is visible, not just pass/fail.

| Option | Effect |
|--------|--------|
| `--max-attempts N` | tries per task (1 = no self-checking) |
| `--plan` | plan first: rules, hand-worked examples, steps; failures fix the plan |
| `--feedback detailed/simple` | full pytest failure output, or failing test names only |
| `--no-anti-stuck` | don't catch repeated code; keep temperature 0 on retries |
| `--safety` | override every task's safety level |
| `--runs N` / `--jobs N` | repeat N times / run N tasks in parallel |

## Research findings

This project started as a research question: does a self-checking loop help a small local
model, and which loop design helps most? Short answer with gemma3:4b: self-checking added
+4 to +8 passed tests on the tricky tasks for every method; planning first gave the best
results (and was the only method that improved the first try) but took ~4x longer; and the
model often got stuck repeating itself until repeat detection was added.

Full experiments, numbers and analysis: [docs/RESEARCH.md](docs/RESEARCH.md).

## Use it from Python

```python
from safe_coding_agent import CodingAgent, Settings, load_task, parse_model
from safe_coding_agent.sandbox import get_runner

task = load_task("my-task")
runner, _ = get_runner("auto")
result = CodingAgent(task, Settings(model=parse_model("ollama:gemma3:4b"), plan_first=True), runner).run()
print(result.status, f"{result.best_passed}/{result.total}")
print(result.best_files)          # {"path": "code", ...}
```

## Development

```bash
pip install -e ".[all,dev]"
pytest -q                 # 120+ tests, no model or API key needed (a scripted fake model is used)
ruff check src tests
```

The Docker isolation tests run when the sandbox image is built (`sca sandbox build`).

## Roadmap

- [x] Self-checking loop, detailed feedback, anti-stuck, plan-first (research v0.1-v0.5)
- [x] v1.0: installable CLI, your own multi-file tasks with pytest, Ollama / OpenAI-compatible / Anthropic,
  AST safety check, Docker sandbox, partial-credit benchmark and comparison
- [ ] Repo mode: work directly on an existing project folder instead of a task folder
- [ ] Human-in-the-loop approval for risky actions (LangGraph `interrupt`)
- [ ] Prompt-injection test set: hostile instructions hidden in starter files and test output

## License

MIT
