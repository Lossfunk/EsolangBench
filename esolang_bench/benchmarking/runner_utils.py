"""
Benchmark runner utilities for EsoLang-Bench.

Implements all evaluation regimes:
- zero_shot: Direct code generation
- few_shot: With 3 ICL examples
- self_scaffolding: Direct interpreter feedback, 1 LLM call per iteration (best performer)
- textual_self_scaffolding: Coder-critic pair, 2 LLM calls per iteration
- react: ReAct pipeline with planner, coder, and critic
"""
from __future__ import annotations

import json
from datetime import datetime
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple

from esolang_bench.interpreters import get_interpreter

from .config import RESULTS_DIR, LANGUAGE_METADATA, get_max_tokens, get_max_attempts, get_doc_path, get_icl_path
from .dataset_loader import load_problems_for_language, Problem
from .metrics import BenchmarkMetrics
from .openrouter_client import call_llm, OpenRouterError
from .output_utils import outputs_match_lang
from .prompt_templates import (
    build_zero_shot_prompts,
    build_few_shot_prompts,
    build_self_scaffolding_prompt,
    build_textual_self_scaffolding_coder_prompt,
    build_textual_self_scaffolding_critic_prompt,
    build_react_planner_prompt,
    build_react_coder_prompt,
    build_react_critic_prompt,
)


def _load_doc_text(language_id: str) -> str:
    doc_path = get_doc_path(language_id)
    if doc_path.exists():
        return doc_path.read_text(encoding="utf-8")
    return ""


def _load_icl_examples(language_id: str) -> List[Dict[str, Any]]:
    path = get_icl_path(language_id)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("icl_examples", [])


def _problem_to_dict(problem: Problem) -> Dict[str, Any]:
    return {
        "id": problem.id,
        "title": problem.title,
        "description": problem.description,
        "difficulty": problem.difficulty,
        "tests": problem.tests,
    }


def _truncate_preview(text: str, limit: int = 80) -> str:
    preview = (text or "").replace("\n", "\\n")
    return preview if len(preview) <= limit else preview[: limit - 3] + "..."


def _run_tests(language_id: str, code: str, tests: List[Dict[str, str]]) -> Tuple[bool, List[Dict[str, Any]]]:
    interpreter = get_interpreter(language_id)
    all_passed = True
    per_tests = []
    passed_tests = 0
    total_tests = len(tests)
    for idx, test in enumerate(tests, 1):
        stdin = test.get("input", "")
        expected = test.get("output", "")
        passed = False
        try:
            result = interpreter.run(code, stdin=stdin)
            stdout = result.stdout
            error_type = result.error_type
            stderr = result.stderr
        except Exception as exc:  # pragma: no cover - interpreter failure path
            stdout = ""
            stderr = str(exc)
            error_type = "internal_error"
        if error_type == "ok" and outputs_match_lang(expected, stdout, language_id=language_id):
            passed = True
        if passed:
            passed_tests += 1
        else:
            all_passed = False
        status = "PASS" if passed else "FAIL"
        print(
            f"[{language_id}] {status} Test {idx}/{total_tests} | "
            f"expected={_truncate_preview(expected)} | actual={_truncate_preview(stdout)} | error={error_type}"
        )
        per_tests.append(
            {
                "input": stdin,
                "expected_output": expected,
                "actual_output": stdout,
                "error_type": error_type,
                "stderr": stderr,
            }
        )
    if total_tests:
        print(f"[{language_id}] Interpreter tests passed: {passed_tests}/{total_tests}")
    else:
        print(f"[{language_id}] No tests supplied for evaluation.")
    return all_passed, per_tests


def _result_path(regime: str, model_name: str, language_id: str) -> Path:
    return RESULTS_DIR / regime / model_name / f"{language_id}.jsonl"


def _write_result(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        json.dump(record, f)
        f.write("\n")


def _call_model(model_name: str, system_prompt: str, user_messages: List[str], *, max_tokens: int) -> str:
    try:
        return call_llm(model_name, system_prompt, user_messages, max_tokens=max_tokens)
    except OpenRouterError as exc:
        raise RuntimeError(f"OpenRouter call failed: {exc}") from exc


def _clean_llm_code(content: str, *, language_id: str | None = None) -> str:
    content = content.strip()
    if content.startswith("```"):
        parts = content.split("```")
        if len(parts) >= 3:
            candidate = parts[1]
            content = candidate.split("\n", 1)[1] if candidate.startswith("python") else candidate
        else:
            content = parts[-2]
    lines = content.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if language_id and lines:
        normalized = lines[0].strip().lower().rstrip(":")
        metadata = LANGUAGE_METADATA.get(language_id, {})
        canonical_names = {language_id.lower()}
        pretty_name = metadata.get("name")
        if pretty_name:
            canonical_names.add(pretty_name.lower())
        extras = set(canonical_names)
        for name in list(canonical_names):
            extras.add(f"{name} code")
            extras.add(f"language: {name}")
        canonical_names |= extras
        if normalized in canonical_names:
            lines.pop(0)
    return "\n".join(lines).lstrip()


def _preview_code(code: str, header: str) -> None:
    print(f"{header}\n{code}\n{'-' * 40}")


def _latest_test_stats(per_attempt: List[Dict[str, Any]], *, language_id: str | None = None) -> Tuple[int, int]:
    if not per_attempt:
        return 0, 0
    tests = per_attempt[-1].get("tests", [])
    if not tests:
        return 0, 0
    passed = sum(
        1
        for test in tests
        if test.get("error_type") == "ok"
        and outputs_match_lang(test.get("expected_output"), test.get("actual_output"), language_id=language_id)
    )
    return passed, len(tests)


def _format_attempt_report(code: str, per_tests: List[Dict[str, Any]]) -> str:
    lines = ["=== Program ===", code, "", "=== Interpreter Feedback ==="]
    for idx, test in enumerate(per_tests, 1):
        lines.append(
            f"Test {idx}:\n"
            f"Input: {test['input']}\n"
            f"Expected: {test['expected_output']}\n"
            f"Actual: {test['actual_output']}\n"
            f"Error Type: {test['error_type']}\n"
            f"Stderr: {test['stderr']}\n"
        )
    return "\n".join(lines)


# =============================================================================
# Main Benchmark Runner
# =============================================================================

def run_language_benchmark(model_name: str, language_id: str, regime: str, difficulty: str | None = None) -> None:
    """Run benchmark for a specific model, language, and regime combination."""
    print(f"\n=== {regime} :: {model_name} :: {language_id} ===")
    problems = load_problems_for_language(language_id, difficulty=difficulty)

    # Optional limiter to speed up long-running providers
    max_problems_env = os.environ.get("ESOLANG_MAX_PROBLEMS")
    if max_problems_env:
        try:
            problems = problems[: max(0, int(max_problems_env))]
        except ValueError:
            pass

    doc_text = _load_doc_text(language_id)
    icl_examples = _load_icl_examples(language_id)
    metrics = BenchmarkMetrics(regime=regime)
    result_file = _result_path(regime, model_name, language_id)

    for idx, problem in enumerate(problems, 1):
        problem_dict = _problem_to_dict(problem)
        try:
            if regime == "zero_shot":
                result = _run_zero_shot(model_name, language_id, doc_text, problem_dict)
            elif regime == "few_shot":
                result = _run_few_shot(model_name, language_id, doc_text, problem_dict, icl_examples)
            elif regime == "self_scaffolding":
                result = _run_self_scaffolding(
                    model_name,
                    language_id,
                    doc_text,
                    problem_dict,
                    icl_examples,
                    max_attempts=get_max_attempts("self_scaffolding"),
                )
            elif regime == "textual_self_scaffolding":
                result = _run_textual_self_scaffolding(
                    model_name,
                    language_id,
                    doc_text,
                    problem_dict,
                    icl_examples,
                    max_attempts=get_max_attempts("textual_self_scaffolding"),
                )
            elif regime == "react":
                result = _run_react(
                    model_name,
                    language_id,
                    doc_text,
                    problem_dict,
                    icl_examples,
                    max_attempts=get_max_attempts("react"),
                )
            else:
                raise ValueError(f"Unknown regime: {regime}")

            solved = result["solved"]
            attempts = result["attempts"]
            failure_errors = []
            if not solved and result["per_attempt"]:
                failure_errors = [t["error_type"] for t in result["per_attempt"][-1]["tests"]]
            metrics.record_result(solved, attempts, failure_errors)
            record = {
                "timestamp": datetime.utcnow().isoformat(),
                "regime": regime,
                "model": model_name,
                "language": language_id,
                "problem_id": problem.id,
                "difficulty": problem.difficulty,
                **result,
            }
            _write_result(result_file, record)
            status = "SOLVED" if solved else "FAILED"
            passed_tests, total_tests = _latest_test_stats(result.get("per_attempt", []), language_id=language_id)
            running_acc = metrics.accuracy() * 100
            print(
                f"[{regime}] {model_name}/{language_id} Problem {problem.id} -> {status} "
                f"(tests {passed_tests}/{total_tests}, attempts={attempts}, running acc={running_acc:.1f}%)"
            )
        except Exception as exc:
            metrics.record_result(False, 0, ["internal_error"])
            record = {
                "timestamp": datetime.utcnow().isoformat(),
                "regime": regime,
                "model": model_name,
                "language": language_id,
                "problem_id": problem.id,
                "difficulty": problem.difficulty,
                "solved": False,
                "attempts": 0,
                "per_attempt": [],
                "error": str(exc),
            }
            _write_result(result_file, record)
            print(f"[{regime}] {model_name}/{language_id} Problem {problem.id} crashed: {exc}")

    print(metrics.summary())


# =============================================================================
# Zero-Shot Runner
# =============================================================================

def _run_zero_shot(model_name: str, language_id: str, doc_text: str, problem: Dict[str, Any]) -> Dict[str, Any]:
    """Run zero-shot code generation."""
    system_prompt, messages = build_zero_shot_prompts(language_id, doc_text, problem)
    max_tokens = get_max_tokens(model_name, "zero_shot", language_id=language_id)
    raw_response = _call_model(model_name, system_prompt, messages, max_tokens=max_tokens)
    code = _clean_llm_code(raw_response, language_id=language_id)
    _preview_code(code, f"[zero_shot] Generated {language_id} code for {model_name}")
    passed, per_tests = _run_tests(language_id, code, problem["tests"])
    return {
        "solved": passed,
        "attempts": 1,
        "per_attempt": [
            {
                "attempt_index": 1,
                "code": code,
                "tests": per_tests,
            }
        ],
    }


# =============================================================================
# Few-Shot Runner (3 ICL examples)
# =============================================================================

def _run_few_shot(
    model_name: str,
    language_id: str,
    doc_text: str,
    problem: Dict[str, Any],
    icl_examples: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Run few-shot code generation with 3 ICL examples."""
    system_prompt, messages = build_few_shot_prompts(language_id, doc_text, problem, icl_examples)
    max_tokens = get_max_tokens(model_name, "few_shot", language_id=language_id)
    raw_response = _call_model(model_name, system_prompt, messages, max_tokens=max_tokens)
    code = _clean_llm_code(raw_response, language_id=language_id)
    _preview_code(code, f"[few_shot] Generated {language_id} code for {model_name}")
    passed, per_tests = _run_tests(language_id, code, problem["tests"])
    return {
        "solved": passed,
        "attempts": 1,
        "per_attempt": [
            {
                "attempt_index": 1,
                "code": code,
                "tests": per_tests,
            }
        ],
    }


# =============================================================================
# Self-Scaffolding Runner (1 LLM call per iteration - BEST PERFORMER)
# =============================================================================

def _run_self_scaffolding(
    model_name: str,
    language_id: str,
    doc_text: str,
    problem: Dict[str, Any],
    icl_examples: List[Dict[str, Any]],
    max_attempts: int | None = None,
) -> Dict[str, Any]:
    """
    Run self-scaffolding with direct interpreter feedback.

    This is the best-performing non-agentic strategy. Uses a single LLM call
    per iteration - the model receives raw interpreter output and must
    self-diagnose issues without a separate critic.
    """
    if max_attempts is None:
        max_attempts = get_max_attempts("self_scaffolding")

    attempt_context: str | None = None
    attempts_log: List[Dict[str, Any]] = []
    solved = False

    for attempt in range(1, max_attempts + 1):
        # Only include ICL examples on first attempt
        include_examples = attempt == 1
        examples_payload = icl_examples if include_examples else None

        system_prompt, messages = build_self_scaffolding_prompt(
            language_id,
            doc_text,
            problem,
            examples_payload,
            attempt_context,
        )
        max_tokens = get_max_tokens(model_name, "self_scaffolding", language_id=language_id)
        raw_response = _call_model(model_name, system_prompt, messages, max_tokens=max_tokens)
        code = _clean_llm_code(raw_response, language_id=language_id)
        _preview_code(code, f"[self_scaffolding attempt {attempt}] {model_name}/{language_id} code")

        passed, per_tests = _run_tests(language_id, code, problem["tests"])
        attempts_log.append(
            {
                "attempt_index": attempt,
                "code": code,
                "tests": per_tests,
            }
        )

        if passed:
            solved = True
            break

        # Prepare feedback for next iteration
        attempt_context = _format_attempt_report(code, per_tests)

    return {
        "solved": solved,
        "attempts": len(attempts_log),
        "per_attempt": attempts_log,
    }


# =============================================================================
# Textual Self-Scaffolding Runner (2 LLM calls per iteration: coder + critic)
# =============================================================================

def _run_textual_self_scaffolding(
    model_name: str,
    language_id: str,
    doc_text: str,
    problem: Dict[str, Any],
    icl_examples: List[Dict[str, Any]],
    max_attempts: int | None = None,
) -> Dict[str, Any]:
    """
    Run textual self-scaffolding with coder-critic pair.

    Uses two LLM calls per iteration:
    1. Coder generates code
    2. Critic analyzes failures and provides natural-language feedback
    """
    if max_attempts is None:
        max_attempts = get_max_attempts("textual_self_scaffolding")

    feedback: str | None = None
    previous_code: str | None = None
    attempts_log: List[Dict[str, Any]] = []
    solved = False

    for attempt in range(1, max_attempts + 1):
        # Coder generates code
        system_prompt, messages = build_textual_self_scaffolding_coder_prompt(
            language_id,
            doc_text,
            problem,
            icl_examples,
            feedback,
            previous_code,
        )
        max_tokens = get_max_tokens(model_name, "textual_self_scaffolding", language_id=language_id)
        raw_response = _call_model(model_name, system_prompt, messages, max_tokens=max_tokens)
        code = _clean_llm_code(raw_response, language_id=language_id)
        _preview_code(code, f"[textual_self_scaffolding attempt {attempt}] {model_name}/{language_id} code")

        passed, per_tests = _run_tests(language_id, code, problem["tests"])

        critic_text = ""
        if not passed:
            # Critic analyzes the failure
            attempt_report = _format_attempt_report(code, per_tests)
            critic_system, critic_messages = build_textual_self_scaffolding_critic_prompt(
                language_id, problem, attempt_report
            )
            critic_text = _call_model(model_name, critic_system, critic_messages, max_tokens=max_tokens)
            print(f"[textual_self_scaffolding attempt {attempt}] Critic feedback:\n{critic_text}\n{'-'*40}")
            feedback = critic_text
            previous_code = code

        attempts_log.append(
            {
                "attempt_index": attempt,
                "code": code,
                "tests": per_tests,
                "critic_feedback": critic_text,
            }
        )

        if passed:
            solved = True
            break

    return {
        "solved": solved,
        "attempts": len(attempts_log),
        "per_attempt": attempts_log,
    }


# =============================================================================
# ReAct Pipeline Runner (planner + coder + critic)
# =============================================================================

def _run_react(
    model_name: str,
    language_id: str,
    doc_text: str,
    problem: Dict[str, Any],
    icl_examples: List[Dict[str, Any]],
    max_attempts: int | None = None,
) -> Dict[str, Any]:
    """
    Run ReAct pipeline with planner, coder, and critic.

    Three-stage approach inspired by Yao et al. (2023):
    1. Planner generates high-level algorithm in pseudocode
    2. Coder translates plan into target esoteric language
    3. Critic analyzes failures and feeds back to planner
    """
    if max_attempts is None:
        max_attempts = get_max_attempts("react")

    previous_plan: str | None = None
    critic_feedback: str | None = None
    attempts_log: List[Dict[str, Any]] = []
    solved = False

    for attempt in range(1, max_attempts + 1):
        max_tokens = get_max_tokens(model_name, "react", language_id=language_id)

        # Stage 1: Planner generates algorithm
        planner_system, planner_messages = build_react_planner_prompt(
            language_id,
            doc_text,
            problem,
            previous_plan,
            critic_feedback,
        )
        plan = _call_model(model_name, planner_system, planner_messages, max_tokens=max_tokens)
        print(f"[react attempt {attempt}] Planner output:\n{plan}\n{'-'*40}")

        # Stage 2: Coder translates to target language
        coder_system, coder_messages = build_react_coder_prompt(
            language_id,
            doc_text,
            problem,
            plan,
            icl_examples if attempt == 1 else None,
        )
        raw_response = _call_model(model_name, coder_system, coder_messages, max_tokens=max_tokens)
        code = _clean_llm_code(raw_response, language_id=language_id)
        _preview_code(code, f"[react attempt {attempt}] {model_name}/{language_id} code")

        passed, per_tests = _run_tests(language_id, code, problem["tests"])

        critic_text = ""
        if not passed:
            # Stage 3: Critic analyzes failure
            attempt_report = _format_attempt_report(code, per_tests)
            critic_system, critic_messages = build_react_critic_prompt(
                language_id, problem, plan, attempt_report
            )
            critic_text = _call_model(model_name, critic_system, critic_messages, max_tokens=max_tokens)
            print(f"[react attempt {attempt}] Critic feedback:\n{critic_text}\n{'-'*40}")
            critic_feedback = critic_text
            previous_plan = plan

        attempts_log.append(
            {
                "attempt_index": attempt,
                "plan": plan,
                "code": code,
                "tests": per_tests,
                "critic_feedback": critic_text,
            }
        )

        if passed:
            solved = True
            break

    return {
        "solved": solved,
        "attempts": len(attempts_log),
        "per_attempt": attempts_log,
    }


def main() -> None:
    """Entry point for ``esolang-run`` console script."""
    import argparse

    from .config import ALL_LANGUAGES, ALL_MODELS, REGIMES, DIFFICULTY_LEVELS

    parser = argparse.ArgumentParser(
        prog="esolang-run",
        description="Run EsoLang-Bench evaluation for a given model, language, and regime.",
    )
    parser.add_argument("--model", "-m", required=True, choices=ALL_MODELS, help="Model name")
    parser.add_argument("--language", "-l", required=True, choices=ALL_LANGUAGES, help="Language")
    parser.add_argument("--regime", "-r", required=True, choices=REGIMES, help="Prompting regime")
    parser.add_argument(
        "--difficulty", "-d",
        choices=["all"] + DIFFICULTY_LEVELS,
        default="all",
        help="Difficulty filter (default: all)",
    )
    args = parser.parse_args()
    run_language_benchmark(args.model, args.language, args.regime, difficulty=args.difficulty)
