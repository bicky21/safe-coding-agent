# Research notes

These are the experiments that shaped the agent, run with **gemma3:4b** on a laptop
(Ollama). They were run with the original single-file version (v0.1 to v0.5), which is kept
in [`legacy/`](../legacy) together with every raw result in [`legacy/results/`](../legacy/results).

To re-run the old scripts:

```bash
cd legacy
python agent.py --level tricky --runs 3 --plan
python compare.py --level tricky
```

With v1.0 the same experiments are run with `sca bench`, e.g.
`sca bench --level tricky --runs 3 --plan`, then `sca compare`. Note that v1.0 runs the
tests with pytest and counts tests slightly differently (51 tests on the tricky tasks instead
of 43, because each `pytest.raises` case is its own test), so v1.0 scores are not directly
comparable with the numbers below.

## The research question

Does a **self-checking loop** (write code, run tests, feed the failures back, retry) help a
small local model solve coding tasks, and which loop design helps most?

## Methods compared

- **No self-checking:** one attempt.
- **Simple vs detailed feedback:** raw error vs which test failed with got/expected values.
- **Anti-stuck:** detect when the model repeats an earlier attempt, and raise the
  temperature on retries (0.0, 0.5, 0.8).
- **Plan-first:** before coding, write RULES, hand-worked EXAMPLES and STEPS; on failure,
  fix the plan using the failing case.

## Findings (gemma3:4b)

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
9. **Fair comparison, 3+ runs per method (v0.5, partial-credit scores, 43 tests on the tricky tasks).**

   | Method | Runs | First try | Best (avg) | Best range | Time per run |
   |--------|------|-----------|------------|------------|--------------|
   | Plan-first + anti-stuck, detailed | 4 | **14/43** | **18.8/43** | 18-21 | ~13 min |
   | Anti-stuck, detailed feedback | 4 | 11/43 | 16.5/43 | 15-18 | ~3.3 min |
   | Anti-stuck, simple feedback | 3 | 11/43 | 15.0/43 | 15-15 | ~3.6 min |

   - **Self-checking always helps:** every method gains +4 to +8 tests over its first try.
   - **Plan-first scores best and is the only method that improves the first try** (14 vs 11). Its worst run (18) equals the other methods' best run, so the gain is consistent, but small (+2.3 tests) and it costs ~4x the time.
   - **The gain is uneven:** plan-first helps a lot on rle (5 vs 3 of 8) and weekday (5 vs 1-4 of 8), but hurts wrap (2 vs 4 of 7). duration is stuck at 1/6 for every method.
   - **Detailed vs simple feedback:** 16.5 vs 15.0, a small difference.
   - **Repeats still happen:** even with higher retry temperatures, about 28% of retries (10 of 36 per method) were copies of an earlier attempt. Anti-stuck catches them, but they still use up an attempt.
   - **Runs barely vary.** Most tasks score the same in every run, so more runs of the same 6 tasks add little. More (and more varied) tasks would make the comparison stronger than more runs.

