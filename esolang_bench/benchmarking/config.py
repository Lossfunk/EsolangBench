from __future__ import annotations

import importlib.resources
import os
from pathlib import Path

_DATA_PKG = importlib.resources.files("esolang_bench.data")
_DOCS_PKG = importlib.resources.files("esolang_bench.docs")
_ICL_PKG = importlib.resources.files("esolang_bench.icl_examples")

_DEFAULT_DATASET = _DATA_PKG / "esolang_easy.json"
DATASET_PATH = Path(os.environ.get("ESOLANG_DATASET_PATH", str(_DEFAULT_DATASET)))
DOCS_DIR = _DOCS_PKG
ICL_DIR = _ICL_PKG
RESULTS_DIR = Path(os.environ.get("ESOLANG_RESULTS_DIR", "results"))

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"


def _resolve_model_id(logical_name: str, default: str) -> str:
    env_var = f"OPENROUTER_MODEL_{logical_name.upper().replace('-', '_').replace('.', '_')}"
    return os.environ.get(env_var, default)


MODEL_NAME_TO_ID = {
    "planner-general": _resolve_model_id("planner-general", "openai/gpt-5.2"),
    "python-solver": _resolve_model_id("python-solver", "openai/gpt-5.2"),
    "gemini-3-pro-preview": _resolve_model_id("gemini-3-pro-preview", "google/gemini-3-pro-preview"),
    "gemini-3-flash-preview": _resolve_model_id("gemini-3-flash-preview", "google/gemini-3-flash-preview"),
    "gpt-5.2": _resolve_model_id("gpt-5.2", "openai/gpt-5.2"),
    "claude-opus-4.5": _resolve_model_id("claude-opus-4.5", "anthropic/claude-opus-4.5"),
    "qwen3-235b-a22b-2507": _resolve_model_id("qwen3-235b-a22b-2507", "qwen/qwen3-235b-a22b-2507"),
    "kimi-k2-thinking": _resolve_model_id("kimi-k2-thinking", "moonshotai/kimi-k2-thinking"),
    "kimi-k2": _resolve_model_id("kimi-k2", "moonshotai/kimi-k2"),
    "grok-4": _resolve_model_id("grok-4", "x-ai/grok-4"),
    "o3": _resolve_model_id("o3", "openai/o3"),
    "o4-mini-high": _resolve_model_id("o4-mini-high", "openai/o4-mini-high"),
}

LANGUAGE_METADATA = {
    "brainfuck": {"name": "Brainfuck", "doc_file": "brainfuck.md"},
    "whitespace": {"name": "Whitespace", "doc_file": "whitespace.md"},
    "befunge98": {"name": "Befunge-98", "doc_file": "befunge98.md"},
    "unlambda": {"name": "Unlambda", "doc_file": "unlambda.md"},
    "shakespeare": {
        "name": "Shakespeare Programming Language",
        "doc_file": "shakespeare.md",
    },
}


def get_doc_path(language_id: str) -> Path:
    """Return an on-disk path for the language reference doc."""
    doc_file = LANGUAGE_METADATA[language_id]["doc_file"]
    traversable = DOCS_DIR / doc_file
    return Path(str(traversable))


def get_icl_path(language_id: str) -> Path:
    """Return an on-disk path for in-context learning examples."""
    return Path(str(ICL_DIR / f"{language_id}_icl.json"))

ALL_LANGUAGES = list(LANGUAGE_METADATA.keys())
PRIMARY_CODE_MODELS = [
    "gemini-3-pro-preview",
    "gpt-5.2",
    "grok-4",
    "claude-opus-4.5",
    "qwen3-235b-a22b-2507",
    "kimi-k2-thinking",
    "o3",
    "o4-mini-high",
]
PLANNER_MODEL = "planner-general"
PYTHON_SOLVER_MODEL = "python-solver"
ALL_MODELS = list(MODEL_NAME_TO_ID.keys())
REGIMES = ["zero_shot", "few_shot", "self_scaffolding", "textual_self_scaffolding", "react"]

MAX_TOKENS_PER_REGIME = {
    "zero_shot": 8192,
    "few_shot": 8192,
    "self_scaffolding": 8192,
    "textual_self_scaffolding": 8192,
    "react": 8192,
}

# Optional per-model overrides to speed up slower providers (e.g., grok-4).
# Values can be further overridden by environment variables
# MAX_TOKENS_{MODEL}_{REGIME}, e.g., MAX_TOKENS_GROK_4_ZERO_SHOT=768.
MODEL_MAX_TOKENS_OVERRIDES = {}

# Optional per-model+language default overrides (used if no env var is set)
MODEL_LANGUAGE_MAX_TOKENS_OVERRIDES = {
    "grok-4": {
        "brainfuck": {
            "zero_shot": 512,
            "few_shot": 512,
            "self_scaffolding": 512,
            "textual_self_scaffolding": 512,
            "react": 512,
        }
    }
}


MAX_ATTEMPTS_PER_REGIME = {
    # Paper uses 5 attempts for all iterative regimes
    "self_scaffolding": 5,
    "textual_self_scaffolding": 5,
    "react": 5,
}


DIFFICULTY_LEVELS = ["easy", "medium", "hard", "extra_hard"]

DATASET_FILES = {
    "easy": "esolang_easy_dataset.json",
    "medium": "esolang_medium_dataset.json",
    "hard": "esolang_hard_dataset.json",
    "extra_hard": "esolang_extra_hard_dataset.json",
}


def get_dataset_path(difficulty: str) -> Path:
    """Return the on-disk path for a difficulty-specific dataset file."""
    filename = DATASET_FILES[difficulty]
    traversable = _DATA_PKG / filename
    return Path(str(traversable))


def get_max_tokens(model_name: str, regime: str, *, language_id: str | None = None) -> int:
    # Env var precedence: model+regime, then regime-wide, then override map, then default
    model_key = model_name.upper().replace("-", "_").replace(".", "_")
    regime_key = regime.upper()
    lang_key = (language_id or "").upper().replace("-", "_").replace(".", "_")

    # Most specific: model + language + regime
    if language_id:
        env_key_model_lang = f"MAX_TOKENS_{model_key}_{lang_key}_{regime_key}"
        val = os.environ.get(env_key_model_lang)
        if val:
            try:
                return int(val)
            except ValueError:
                pass

    # Model + regime
    env_key_model = f"MAX_TOKENS_{model_key}_{regime_key}"
    val = os.environ.get(env_key_model)
    if val:
        try:
            return int(val)
        except ValueError:
            pass

    # Language + regime (applies to all models)
    if language_id:
        env_key_lang = f"MAX_TOKENS_{lang_key}_{regime_key}"
        val = os.environ.get(env_key_lang)
        if val:
            try:
                return int(val)
            except ValueError:
                pass
    env_key_regime = f"MAX_TOKENS_{regime_key}"
    val = os.environ.get(env_key_regime)
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    overrides = MODEL_MAX_TOKENS_OVERRIDES.get(model_name, {})
    if regime in overrides:
        return overrides[regime]
    # Model + language specific fallback
    if language_id:
        lang_over = MODEL_LANGUAGE_MAX_TOKENS_OVERRIDES.get(model_name, {}).get(language_id, {})
        if regime in lang_over:
            return lang_over[regime]
    return MAX_TOKENS_PER_REGIME.get(regime, 1024)


def get_max_attempts(regime: str) -> int:
    env_key = f"MAX_ATTEMPTS_{regime.upper()}"
    val = os.environ.get(env_key)
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return MAX_ATTEMPTS_PER_REGIME.get(regime, 5)
