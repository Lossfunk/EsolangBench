from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict
import json
from pathlib import Path

from .config import DATASET_PATH, DIFFICULTY_LEVELS, get_dataset_path


@dataclass(frozen=True)
class Problem:
    id: str
    title: str
    description: str
    difficulty: str
    tests: List[Dict[str, str]]


def _load_raw_dataset(path: Path | None = None) -> dict:
    p = path or DATASET_PATH
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def _parse_problems(raw: dict) -> List[Problem]:
    items = raw.get("problems") or raw.get("items") or []
    problems: List[Problem] = []
    for entry in items:
        tests = entry.get("input_output_examples") or entry.get("tests") or []
        normalized_tests = [
            {"input": test.get("input", ""), "output": test.get("output", "")} for test in tests
        ]
        problems.append(
            Problem(
                id=entry.get("id", ""),
                title=entry.get("title", ""),
                description=entry.get("description", ""),
                difficulty=entry.get("difficulty", "unknown"),
                tests=normalized_tests,
            )
        )
    return problems


def load_all_problems() -> List[Problem]:
    raw = _load_raw_dataset()
    return _parse_problems(raw)


def load_problems_by_difficulty(difficulty: str) -> List[Problem]:
    """Load problems from the dataset file for a specific difficulty level."""
    if difficulty not in DIFFICULTY_LEVELS:
        raise ValueError(f"Unknown difficulty '{difficulty}'. Choose from: {DIFFICULTY_LEVELS}")
    path = get_dataset_path(difficulty)
    raw = _load_raw_dataset(path)
    problems = _parse_problems(raw)
    return [p for p in problems if p.difficulty == difficulty]


def load_problems_for_language(language_id: str, difficulty: str | None = None) -> List[Problem]:
    """Load problems, optionally filtered by difficulty.

    When *difficulty* is ``None`` or ``"all"``, loads from the default
    dataset (``DATASET_PATH``).  Otherwise loads from the
    difficulty-specific file **and** filters to matching problems.
    """
    if difficulty is None or difficulty == "all":
        return load_all_problems()
    return load_problems_by_difficulty(difficulty)
