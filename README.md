# EsoLang-Bench

[![arXiv](https://img.shields.io/badge/arXiv-2603.09678-b31b1b.svg)](https://arxiv.org/abs/2603.09678)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/Lossfunk/EsolangBench/actions/workflows/test.yml/badge.svg)](https://github.com/Lossfunk/EsolangBench/actions)
[![Dataset](https://img.shields.io/badge/🤗%20Dataset-Lossfunk%2FEsolang--Bench-blue)](https://huggingface.co/datasets/Lossfunk/Esolang-Bench)
[![Website](https://img.shields.io/badge/Website-esolang--bench.vercel.app-green)](https://esolang-bench.vercel.app)

**Evaluating Genuine Reasoning in Large Language Models via Esoteric Programming Languages**

📄 **Paper:** [arxiv.org/abs/2603.09678](https://arxiv.org/abs/2603.09678)
🌐 **Website:** [esolang-bench.vercel.app](https://esolang-bench.vercel.app)
📦 **Dataset:** [huggingface.co/datasets/Lossfunk/Esolang-Bench](https://huggingface.co/datasets/Lossfunk/Esolang-Bench)

EsoLang-Bench is a benchmark that tests frontier LLMs on code generation in esoteric programming languages: **Brainfuck**, **Befunge-98**, **Whitespace**, **Unlambda**, and **Shakespeare**. These languages have 1,000x–100,000x fewer public repositories than Python (based on GitHub search counts), exposing whether models can genuinely reason about novel computational paradigms or merely pattern-match from memorized code.

## Key Finding

> The best frontier model (GPT-5.2) achieves **3.8%** on EsoLang-Bench vs. **~90%** on equivalent Python tasks -- an **85 percentage point gap** that reveals fundamental limitations in out-of-distribution code reasoning.

## Installation

**Basic** (interpreters only):

```bash
pip install -e .
```

**Benchmark** (includes OpenRouter API client):

```bash
pip install -e ".[benchmark]"
```

**Development** (includes test dependencies):

```bash
pip install -e ".[benchmark,dev]"
```

## Dataset

The benchmark dataset (80 problems × 4 difficulty tiers) is available on Hugging Face:

```python
from datasets import load_dataset

ds       = load_dataset("Lossfunk/Esolang-Bench")               # all 80 problems
ds_easy  = load_dataset("Lossfunk/Esolang-Bench", "easy")       # 20 Easy
ds_med   = load_dataset("Lossfunk/Esolang-Bench", "medium")     # 20 Medium
ds_hard  = load_dataset("Lossfunk/Esolang-Bench", "hard")       # 20 Hard
ds_xhard = load_dataset("Lossfunk/Esolang-Bench", "extra_hard") # 20 Extra-Hard

# Each row: id, difficulty, title, description, test_cases (list of 6 {input, output} dicts)
print(ds["test"][0])
```

## Quick Start

### Interpreter CLI

```bash
# Brainfuck: print '$' (ASCII 36)
esolang-interpret -l brainfuck -c '++++++[>++++++<-]>.'

# Befunge-98: Hello World
esolang-interpret -l befunge98 -c '"!dlroW ,olleH">:#,_@'

# From file
esolang-interpret -l whitespace -f program.ws

# With stdin
echo "5" | esolang-interpret -l brainfuck -c ',.'
```

### Python API

```python
from esolang_bench import get_interpreter

interp = get_interpreter("brainfuck")
result = interp.run("++++++[>++++++<-]>.", stdin="")
print(result.stdout)      # "$"
print(result.error_type)  # "ok"
```

### Benchmark CLI

```bash
export OPENROUTER_API_KEY=sk-or-...

# Run a single evaluation
esolang-run --model gpt-5.2 --language brainfuck --regime self_scaffolding

# Filter by difficulty
esolang-run --model gpt-5.2 --language brainfuck --regime zero_shot --difficulty easy

# Limit problems for quick testing
ESOLANG_MAX_PROBLEMS=5 esolang-run -m gpt-5.2 -l brainfuck -r zero_shot
```

## Evaluation Regimes

EsoLang-Bench evaluates models under 5 prompting regimes plus a baseline:

| Regime | LLM Calls/Iter | Description |
|--------|---------------|-------------|
| `zero_shot` | 1 (single) | Direct code generation with language docs |
| `few_shot` | 1 (single) | Zero-shot + 3 in-context learning examples |
| `self_scaffolding` | 1 | Direct interpreter feedback, model self-diagnoses (best non-agentic) |
| `textual_self_scaffolding` | 2 | Coder + critic pair; critic provides NL debugging guidance |
| `react` | 3 | Planner + coder + critic pipeline (ReAct-style) |

All iterative regimes (`self_scaffolding`, `textual_self_scaffolding`, `react`) run up to **5 attempts** per problem (configurable via environment variables).

## Difficulty Levels

Problems are organized into 4 difficulty tiers:

| Level | Flag | Description |
|-------|------|-------------|
| Easy | `--difficulty easy` | Basic I/O, simple loops |
| Medium | `--difficulty medium` | String manipulation, conditionals |
| Hard | `--difficulty hard` | Complex algorithms, nested structures |
| Extra Hard | `--difficulty extra_hard` | Advanced data structures, multi-step reasoning |

Use `--difficulty all` (default) to run all problems.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | *(required)* | OpenRouter API key |
| `ESOLANG_MAX_PROBLEMS` | unlimited | Limit number of problems per run |
| `ESOLANG_RESULTS_DIR` | `./results` | Output directory for result JSONL files |
| `MAX_ATTEMPTS_SELF_SCAFFOLDING` | `5` | Max iterations for self-scaffolding |
| `MAX_ATTEMPTS_TEXTUAL_SELF_SCAFFOLDING` | `5` | Max iterations for textual self-scaffolding |
| `MAX_ATTEMPTS_REACT` | `5` | Max iterations for ReAct pipeline |
| `MAX_TOKENS_{REGIME}` | `8192` | Max tokens for a regime (e.g., `MAX_TOKENS_ZERO_SHOT`) |
| `MAX_TOKENS_{MODEL}_{REGIME}` | -- | Per-model token override |

## Supported Languages

| Language | Paradigm | GitHub Repos | Best Accuracy |
|----------|----------|-------------|---------------|
| Brainfuck | Tape machine | ~5,000 | 13.8% (agentic) |
| Befunge-98 | 2D grid | ~2,000 | 11.2% |
| Whitespace | Invisible syntax | ~200 | 0% |
| Unlambda | Combinators | ~100 | 1.2% |
| Shakespeare | Theatrical | ~150 | 2.5% |

## Results Summary

| Model | Best Strategy | Overall Accuracy |
|-------|--------------|-----------------|
| GPT-5.2 | Self-Scaffolding | 3.8% |
| O4-mini-high | Self-Scaffolding | 3.2% |
| Gemini 3 Pro | Self-Scaffolding | 2.8% |
| Qwen3-235B | Self-Scaffolding | 1.0% |
| Kimi K2 Thinking | Self-Scaffolding | 0.8% |
| Codex (Agentic) | -- | 13.8% |
| Claude Code | -- | 12.5% |

## Project Structure

```
esolang_bench/
  interpreters/     # Pure-Python interpreters for 5 esolangs
  benchmarking/     # LLM evaluation harness
    config.py       # Models, regimes, difficulty levels, token limits
    runner_utils.py # All 5 regime runners + CLI entry point
    prompt_templates.py  # Prompt builders for each regime
    dataset_loader.py    # Problem loading with difficulty filtering
    metrics.py      # Accuracy and attempt tracking
  data/             # 80 problems x 4 difficulty tiers
  docs/             # Language reference documentation
  icl_examples/     # Few-shot examples per language
tests/              # Interpreter test suite
```

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Citation

```bibtex
@article{sharma2026esolangbench,
  title={{EsoLang-Bench}: Evaluating Genuine Reasoning in Large Language Models via Esoteric Programming Languages},
  author={Sharma, Aman and Chopra, Paras},
  journal={arXiv preprint arXiv:2603.09678},
  year={2026},
  eprint={2603.09678},
  archivePrefix={arXiv},
  primaryClass={cs.LG},
  url={https://arxiv.org/abs/2603.09678}
}
```

## License

Code: [MIT](LICENSE) | Dataset: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
