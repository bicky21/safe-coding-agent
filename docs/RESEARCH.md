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


## Part 2: v1.0, bigger models (29 Oct 2026)

Same agent, now run with `sca` (pytest scoring, 13 built-in tasks = 86 tests, plus the
multi-file `examples/todo-project` = 13 tests). Big models ran on Groq's free tier;
Gemma ran locally on a laptop (HP Victus, Ryzen 5 5600H, RX 6500M).

| Model | Where | Task set | Self-checking | First try | Best | Time |
|-------|-------|----------|---------------|-----------|------|------|
| gemma3:4b | laptop | todo-project | yes | 11/13 | 11/13 | 1.5 min |
| gemma3:4b | laptop | todo-project | yes + plan-first | 9/13 | 9/13 | 12.9 min |
| gpt-oss-20b | Groq | 13 built-in | no | 86/86 | 86/86 | 1.1 min |
| gpt-oss-20b | Groq | 13 built-in | yes | weekday 7/10, fixed on try 2 | (run stopped, see below) | |
| qwen3.8-27b | Groq | 13 built-in | no | 86/86 | 86/86 | 2.8 min |
| qwen3.8-27b | Groq | 13 built-in | yes | 86/86 | 86/86 | 3.7 min |
| gpt-oss-120b | Groq | todo-project | yes | 13/13 | 13/13 | 4 s |
| gpt-oss-120b | Groq | 6 tricky | yes | 51/51 | 51/51 | 20 s |

### Findings

10. **The tool works; the small model was the limit.** On the same multi-file task,
    gemma3:4b got stuck at 11/13 while gpt-oss-120b passed 13/13 on the first try in
    4 seconds. Gemma's two remaining bugs were simple (a reversed sort key, a missing
    "nothing pending" case) and stayed even with full test diffs and an explicit
    "your change fixed nothing" message: a 4B model can write the code but struggles to
    debug it.
11. **The benchmark is saturated for models of 20B and up.** Every model from 20B to 120B
    passed all 86 tests on the first try, including the 6 "tricky" tasks that were built to
    defeat recall from memory (gemma3:4b reached about 16 of 43 on them). Self-checking had
    nothing left to fix. To measure self-checking on bigger models, the tasks have to be
    much harder (larger multi-file projects, stricter specs).
12. **Self-checking still caught a real mistake on a 20B model.** In the self-checking run,
    gpt-oss-20b failed 3 of 10 weekday tests on its first try and fixed them on the second.
    In the run without self-checking the same model passed weekday first time, so a single
    run hides this kind of variation; repeated runs (`--runs`) are needed for firm numbers.
13. **Plan-first did not help gemma3:4b on the multi-file task** (9/13 vs 11/13) and took
    about 8x longer. Gemma wrote a new plan each time but kept returning its previous code,
    which led to the "fresh start after a repeat" and "stop early" changes.
14. **Running a local model can overheat a laptop.** A long gemma3:4b run under full CPU/GPU
    load caused a hardware power-off (no warning in the system log). Cloud models avoid this;
    locally, use good airflow, `SCA_OLLAMA_NUM_THREAD`, and avoid back-to-back runs.

### Bugs found by these real runs (all fixed)

Testing with real models found problems the scripted tests did not:

- Gemma named files in ways the parser didn't expect, so first answers were thrown away.
- Unusable answers and repeats used up real attempts (2 of 3 wasted).
- pytest's short output hid the bug (`['Buy milk', ...]`); tests now run with full diffs.
- Cosmetic changes that fixed nothing counted as progress; they are now called out.
- Ollama's default 4096-token context silently cut long prompts; it is now sized per prompt.
- Groq's free tier (8000 tokens per minute) rejected requests because the reserved answer
  length counts against the limit (`413`); the agent now retries with a shorter answer limit,
  and waits as long as the provider asks on rate limits.
- One model error crashed a whole benchmark and lost all its results; it now marks that
  task as `error`, carries on, and saves everything.

### Next

- A harder benchmark that big models do not saturate (multi-file projects, larger code).
- Several runs per setting (`--runs 3`) to separate real effects from run-to-run variation.
- Mid-size local coding models (e.g. qwen2.5-coder:7b) to find where self-checking stops
  mattering.
