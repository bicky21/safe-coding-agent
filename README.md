# Self-Checking, Safe Coding Agent (v0.1)

A LangGraph coding agent that writes Python code, checks it for dangerous actions, runs tests, and fixes its own mistakes (up to 3 tries). Runs free and offline using Gemma through Ollama.

## How it works

```
START -> write_code -> check_safety --(blocked)--> END
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

`tasks.py` has 7 tasks (easy, medium, hard). Each has tests the code must pass.

```bash
python agent.py                     # run all tasks
python agent.py --task roman        # run one task
python agent.py --level hard        # run only hard tasks
python agent.py --max-attempts 1    # self-checking OFF (for comparison)
python agent.py --show-code         # also print the final code
python agent.py --list              # list task names
```

At the end you get a summary table, and the results are saved in `results/` as a CSV file.

**Experiment idea:** run once with `--max-attempts 1` and once with the default (3). The difference in "Passed" shows how much self-checking helps.

## Roadmap

- [x] v0.1 Write -> safety check -> test -> retry loop
- [x] v0.1.1 Benchmark of 7 tasks, summary table, CSV results
- [ ] v0.2 Replace regex safety check with Python AST checks
- [ ] v0.3 Run tests inside Docker (real sandbox)
- [ ] v0.4 Human-in-the-loop approval for risky actions (LangGraph `interrupt`)
- [ ] v0.5 Prompt-injection test set + measure attacks blocked
- [ ] v0.6 Benchmark: tasks solved with vs without self-checking
