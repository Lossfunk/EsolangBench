# EsoLang-Bench

[![arXiv](https://img.shields.io/badge/arXiv-2603.09678-b31b1b.svg)](https://arxiv.org/abs/2603.09678)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/Lossfunk/EsolangBench/actions/workflows/test.yml/badge.svg)](https://github.com/Lossfunk/EsolangBench/actions)
[![Dataset](https://img.shields.io/badge/🤗%20Dataset-Lossfunk%2FEsolang--Bench-blue)](https://huggingface.co/datasets/Lossfunk/Esolang-Bench)
[![Website](https://img.shields.io/badge/Website-esolang--bench.vercel.app-green)](https://esolang-bench.vercel.app)

**Evaluating Large Language Models via Esoteric Programming Languages**

📄 **Paper:** [arxiv.org/abs/2603.09678](https://arxiv.org/abs/2603.09678)
🌐 **Website:** [esolang-bench.vercel.app](https://esolang-bench.vercel.app)
📦 **Dataset:** [huggingface.co/datasets/Lossfunk/Esolang-Bench](https://huggingface.co/datasets/Lossfunk/Esolang-Bench)

EsoLang-Bench is a contamination-resistant benchmark that evaluates frontier LLMs on code generation in five Turing-complete esoteric programming languages: **Brainfuck**, **Befunge-98**, **Whitespace**, **Unlambda**, and **Shakespeare**. These languages have 340× to over 60,000× fewer public GitHub repositories than Python (verified May 2026 via topic-tag counts) and have negligible commercial deployment value, which together make large-scale contamination highly unlikely at corpus scale.

## Key Finding

> The same 80 problems expressed in Python or JavaScript reach **100%** on top frontier models, while peak esoteric accuracy is only **11.2%** (GPT-5.4 xhigh, self-scaffolding, Befunge-98) — an **89-point collapse** on identical algorithmic content. Few-shot prompting adds only **0.8 pp** over zero-shot (Wilcoxon p=0.505, n.s.).

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

The benchmark dataset (80 problems × 4 difficulty tiers, evaluated independently in 5 esoteric languages = 400 problem-language combinations per prompting strategy) is available on Hugging Face:

```python
from datasets import load_dataset

# All 80 problems (single config, single split)
ds = load_dataset("Lossfunk/Esolang-Bench")["test"]

# Filter by difficulty tier
easy   = ds.filter(lambda r: r["difficulty"] == "easy")
medium = ds.filter(lambda r: r["difficulty"] == "medium")
hard   = ds.filter(lambda r: r["difficulty"] == "hard")
xhard  = ds.filter(lambda r: r["difficulty"] == "extra_hard")

# Each row: id, difficulty, title, description, test_cases (list of 6 {input, output} dicts)
print(ds[0])
```

A complete Croissant 1.1 metadata file with all seven NeurIPS-mandatory Responsible AI fields is shipped alongside the dataset on the HuggingFace Hub.

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

| Language | Paradigm | GitHub topic repos (May 2026) | Peak esoteric accuracy |
|----------|----------|-------------------------------:|-----------------------:|
| Brainfuck | 8-command memory tape | 2,028 | 6.2% |
| Befunge-98 | 2D stack-based grid | 86 | **11.2%** |
| Whitespace | Stack-based, invisible | 125 | 0% |
| Unlambda | Combinatory logic (s, k, i) | 25 | 1.2% |
| Shakespeare | Theatrical-play dialogue | 11 | 2.5% |

For reference: Python is tagged on 684,596 repositories and JavaScript on 648,084. The gap relative to Python ranges from ~340× for Brainfuck to over 60,000× for Shakespeare.

## Results Summary

Best per-model overall accuracy across all five prompting strategies (self-scaffolding is the dominant strategy):

| Model | Best Strategy | Best per-language peak | Overall (across 5 langs) |
|-------|--------------|------------------------|------------------------:|
| GPT-5.4 xhigh | Self-Scaffolding | 11.2% (Befunge-98) | ~3.8% |
| O4-mini-high | Self-Scaffolding | 10.0% (Befunge-98) | ~3.4% |
| Gemini 3.1 Pro | Self-Scaffolding | 7.5% (Befunge-98) | ~2.6% |
| Qwen3-235B | Self-Scaffolding | 2.5% (Brainfuck) | ~1.0% |
| Kimi K2.5 | Self-Scaffolding | 1.2% (Shakespeare) | ~0.2% |

Mainstream-language baselines (Python, JavaScript) reach 100% across all four difficulty tiers on the same 80 problems.

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
@inproceedings{sharma2026esolangbench,
  title        = {{EsoLang-Bench}: Evaluating Large Language Models via Esoteric Programming Languages},
  author       = {Sharma, Aman and Chopra, Paras},
  booktitle    = {NeurIPS 2026 Track on Evaluations and Datasets},
  year         = {2026},
  organization = {Lossfunk}
}
```

## License

Code: [MIT](LICENSE) | Dataset: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
