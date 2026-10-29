# Self-Checking, Safe Coding Agent (v0.4)

A LangGraph coding agent that writes Python code, checks it for dangerous actions, runs tests, and fixes its own mistakes (up to 3 tries). Runs free and offline using Gemma through Ollama.

## How it works

```
START -> write_code -> check_repeat --(same code as before)--> write_code
                           |
                         (new)
                           v
                       check_safety --(blocked)--> END
                           |
                        (safe)
                           v
                       run_tests --(passed / out of tries)--> END
                           |
                        (failed)
                           v
                       write_code  (retry with the error message)
```

## Setup (step by step)

1. Install Ollama from https://ollama.com
2. Download a Gemma model:
   ```bash
   ollama pull gemma3:4b
   ```
3. Create a virtual environment and install packages (Python 3.10+):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Run the agent:
   ```bash
   python agent.py
   ```

To use a different model: `AGENT_MODEL=gemma3:12b python agent.py`

## Running the benchmark

`tasks.py` has 13 tasks. Each has tests the code must pass.

- **easy / medium / hard** (7 tasks): famous problems like LCS, Dijkstra and LRU cache. Models have seen these many times in training, so they mostly recall the answer (this is called *data contamination*).
- **tricky** (6 tasks): problems with unusual, exact rules (custom run-length encoding, a counter-clockwise spiral, version strings with pre-release labels...). The model can't copy a famous answer, so these show whether self-checking really helps.

```bash
python agent.py                     # run all tasks
python agent.py --task roman        # run one task
python agent.py --level tricky      # run only the tricky tasks
python agent.py --max-attempts 1    # self-checking OFF (for comparison)
python agent.py --feedback simple   # raw Python errors only (for comparison)
python agent.py --no-anti-stuck     # old behaviour: allow repeats, temperature 0
python agent.py --plan              # plan first, then write code
python agent.py --show-code         # also print the final code
python agent.py --list              # list task names
```

At the end you get a summary table. Two files are saved in `results/`:
- a `.csv` with the numbers (task, status, attempts, time, settings)
- a `.log.md` with **every attempt's code and the error the model was shown** - read it to see *why* tasks fail

## Feedback modes

When tests fail, what the agent tells the model matters:

| Mode | What the model is told |
|------|------------------------|
| `simple` | the raw Python error, e.g. `AssertionError` on line 7 |
| `detailed` (default) | which test failed, what the code returned, what was expected, and the values of loop variables |

Example of `detailed` feedback:
```
Test failed: assert compress('abc') == 'abc'
  your code returned: '3a'
  expected:           'abc'
```

## Experiments

Run each a few times (model output varies), on the tricky tasks:

| # | Command | What it measures |
|---|---------|------------------|
| 1 | `python agent.py --level tricky --max-attempts 1` | no self-checking (baseline) |
| 2 | `python agent.py --level tricky --feedback simple` | self-checking with raw errors |
| 3 | `python agent.py --level tricky --feedback detailed` | self-checking with detailed feedback |

| 4 | `python agent.py --level tricky --no-anti-stuck` | detailed feedback, but repeats allowed |
| 5 | `python agent.py --level tricky --plan` | plan first, then code |

## Plan-first mode (`--plan`)

Before writing any code, the model writes a plan with three parts:
- **RULES**: every rule from the task as a numbered list
- **EXAMPLES**: 3 small inputs worked by hand, step by step
- **STEPS**: the algorithm

The code is then written from that plan. When a test fails, the model goes back to the **plan**: it works through the failing input by hand, finds which rule or step was wrong, and writes a corrected plan. This targets finding 7: retries that only patch code instead of rethinking the approach. The log file shows each plan next to its code.

Then run `python analyze.py` to see, for every task, each attempt's error and which attempts were copies of an earlier one.

## Findings so far (gemma3:4b)

| Run | Tricky tasks passed |
|-----|---------------------|
| No self-checking (`--max-attempts 1`) | 0/6 |
| Self-checking, simple feedback | 1/6 (twice) |
| Self-checking, detailed feedback | 0/6 |
| v0.3 detailed, anti-stuck OFF | 0/6 (stuck: 4 of 12 retries, 33%) |
| v0.3 detailed, anti-stuck ON | 0/6 (stuck: 1 of 12 retries, 8%) |
| v0.4 plan-first (`--plan`) | 0/6, but more tests passed inside tasks (see 8) |

1. **Famous problems are solved from memory.** All 7 easy/medium/hard tasks passed on the first try. Tasks with unusual rules mostly fail.
2. **The agent got stuck repeating itself.** With `temperature=0`, once the model repeats its code, the next prompt is word-for-word the same, so the answer is the same again. 7 of 23 retries (30%) were identical copies of an earlier attempt (`python analyze.py`). v0.3 adds `check_repeat` and higher temperature on retries to fix this.
3. **The model ignores exact rules** and falls back to the famous version (e.g. a clockwise spiral when the task says "go DOWN first").
4. **Fixes often touch the wrong part** of the code, or fix one bug and add another.
5. The simple vs detailed difference (1 task) is within run-to-run noise; more runs are needed.
6. **Anti-stuck works, but is not enough.** It cut repeated code from 33% to 8% and made attempts more varied (some got further, e.g. weekday passed its first tests on attempt 3), but still 0/6 passed.
7. **The first idea anchors everything.** The model copies the task rules into its docstring, then writes code that ignores them (rle keeps writing `1a1b1c`). In duration, every attempt keeps the same wrong core idea (split the text into 4 parts) and only adds checks around it. Retries make small edits; they never rethink the approach. Next: make the model plan before coding, and test a bigger model.
8. **Plan-first helps a little, but shows a new gap.** Still 0/6, but some tasks got further than ever: rle attempt 3 finally followed "leave out the count when it is 1" and passed 5 of 8 tests (failing only the "split runs longer than 9" rule), and weekday passed its first tests. Three new problems showed up:
   - **Wrong hand-worked examples:** the plan's EXAMPLES had arithmetic mistakes (e.g. `"1h30m" -> 90` instead of 5400).
   - **Steps miss rules:** rle's plan listed the split-at-9 rule and even the right example output (`9aa`), but its STEPS never did the splitting, so the code didn't either.
   - **Code ignores the plan:** duration's plan said to split on the unit letters, but the code still split on spaces into 4 parts, the same wrong idea as every earlier run. Spiral's code still went right first, the famous version.
   A small model (4B) can write a reasonable plan, but doesn't reliably compute examples or follow its own plan.

## Roadmap

- [x] v0.1 Write -> safety check -> test -> retry loop
- [x] v0.1.1 Benchmark of 7 tasks, summary table, CSV results
- [x] v0.1.2 6 "tricky" tasks with unusual rules (to avoid data contamination)
- [x] v0.2 Detailed test feedback (which test, got vs expected) + attempt log
- [x] v0.3 Anti-stuck: detect repeated code, raise temperature on retries, list earlier errors; `analyze.py`
- [x] v0.4 Plan-first mode: rules + worked examples + steps before code; retries fix the plan
- [ ] v0.5 Replace regex safety check with Python AST checks
- [ ] v0.6 Run tests inside Docker (real sandbox)
- [ ] v0.7 Human-in-the-loop approval for risky actions (LangGraph `interrupt`)
- [ ] v0.8 Prompt-injection test set + measure attacks blocked
