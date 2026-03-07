from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

from esolang_bench.interpreters import get_interpreter

from esolang_bench.benchmarking.config import RESULTS_DIR
from esolang_bench.benchmarking.dataset_loader import load_problems_for_language, Problem
from esolang_bench.benchmarking.metrics import BenchmarkMetrics
from esolang_bench.benchmarking.openrouter_client import call_llm, OpenRouterError
from esolang_bench.benchmarking.output_utils import outputs_match_lang
from esolang_bench.benchmarking.runner_utils import (
    _load_doc_text,
    _load_icl_examples,
    _problem_to_dict,
    _clean_llm_code,
    _preview_code,
)
from .config import TOOL_PROFILES, ToolProfile
from .prompts import build_agentic_prompts, format_feedback_from_tests


def _result_path(profile: ToolProfile, model_name: str, language_id: str) -> Path:
    return RESULTS_DIR / "agentic_scaffolding" / profile.key / model_name / f"{language_id}.jsonl"


def _write_record(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        json.dump(record, f)
        f.write("\n")


def _run_tests_for_agent(language_id: str, code: str, tests: List[Dict[str, str]]) -> Tuple[bool, List[Dict[str, Any]]]:
    interpreter = get_interpreter(language_id)
    all_passed = True
    details: List[Dict[str, Any]] = []
    for test in tests:
        stdin = test.get("input", "")
        expected = test.get("output", "")
        try:
            result = interpreter.run(code, stdin=stdin)
            stdout = result.stdout
            error_type = result.error_type
            stderr = result.stderr
        except Exception as exc:  # pragma: no cover
            stdout = ""
            error_type = "internal_error"
            stderr = str(exc)
        passed = error_type == "ok" and outputs_match_lang(expected, stdout, language_id=language_id)
        if not passed:
            all_passed = False
        details.append(
            {
                "input": stdin,
                "expected_output": expected,
                "actual_output": stdout,
                "error_type": error_type,
                "stderr": stderr,
            }
        )
    return all_passed, details


def _call_model(model_name: str, system_prompt: str, messages: List[str], max_tokens: int) -> str:
    try:
        return call_llm(model_name, system_prompt, messages, max_tokens=max_tokens)
    except OpenRouterError as exc:  # pragma: no cover
        raise RuntimeError(f"OpenRouter call failed: {exc}") from exc


def run_agentic_benchmark(
    model_name: str,
    language_id: str,
    profile_name: str,
    max_attempts: int = 5,
    max_tokens: int = 8_192,
) -> None:
    if profile_name not in TOOL_PROFILES:
        raise ValueError(f"Unknown agentic tool profile: {profile_name}")
    profile = TOOL_PROFILES[profile_name]
    print(f"\n=== agentic_scaffolding/{profile.key} :: {model_name} :: {language_id} ===")
    problems = load_problems_for_language(language_id)
    doc_text = _load_doc_text(language_id)
    icl_examples = _load_icl_examples(language_id)
    metrics = BenchmarkMetrics(regime=f"agentic_scaffolding::{profile.key}")
    result_file = _result_path(profile, model_name, language_id)

    for problem in problems:
        problem_dict = _problem_to_dict(problem)
        attempt_log: List[Dict[str, Any]] = []
        solved = False
        previous_code: str | None = None
        feedback: str | None = None

        for attempt in range(1, max_attempts + 1):
            system_prompt, messages = build_agentic_prompts(
                language_id,
                doc_text,
                problem_dict,
                icl_examples,
                profile,
                feedback,
                previous_code,
            )
            response = _call_model(model_name, system_prompt, messages, max_tokens=max_tokens)
            code = _clean_llm_code(response, language_id=language_id)
            _preview_code(code, f"[agentic {profile.key} attempt {attempt}] {model_name}/{language_id}")
            passed, per_tests = _run_tests_for_agent(language_id, code, problem_dict["tests"])
            public_feedback = per_tests if profile.share_interpreter_feedback else []
            attempt_log.append(
                {
                    "attempt_index": attempt,
                    "code": code,
                    "tests": per_tests,
                    "shared_feedback": public_feedback,
                }
            )
            if passed:
                solved = True
                break
            if profile.share_interpreter_feedback:
                feedback = format_feedback_from_tests(per_tests)
            else:
                feedback = profile.no_feedback_message
            previous_code = code

        failure_errors: List[str] = []
        if attempt_log:
            last_tests = attempt_log[-1]["tests"]
            failure_errors = [t["error_type"] for t in last_tests if t.get("error_type") != "ok"]
        metrics.record_result(solved, len(attempt_log), failure_errors)
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "regime": "agentic_scaffolding",
            "tool_profile": profile.key,
            "model": model_name,
            "language": language_id,
            "problem_id": problem.id,
            "difficulty": problem.difficulty,
            "solved": solved,
            "attempts": len(attempt_log),
            "per_attempt": attempt_log,
        }
        _write_record(result_file, record)
        status = "SOLVED" if solved else "FAILED"
        tests = attempt_log[-1]["tests"] if attempt_log else []
        total_tests = len(tests)
        passed_tests = sum(
            1 for test in tests if test.get("error_type") == "ok" and outputs_match_lang(test.get("expected_output"), test.get("actual_output"), language_id=language_id)
        )
        running_acc = metrics.accuracy() * 100
        print(
            f"[agentic {profile.key}] {model_name}/{language_id} Problem {problem.id} -> {status} "
            f"(tests {passed_tests}/{total_tests}, attempts={len(attempt_log)}, running acc={running_acc:.1f}%)"
        )

    print(metrics.summary())
