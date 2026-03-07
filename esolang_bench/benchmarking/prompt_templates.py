"""
Prompt templates for EsoLang-Bench evaluation.

Regimes (matching paper terminology):
- Zero-Shot: Direct code generation without examples
- Few-Shot: With 3 in-context learning examples
- Self-Scaffolding: Direct interpreter feedback, 1 LLM call per iteration (best performer)
- Textual Self-Scaffolding: Coder-critic pair, 2 LLM calls per iteration
- ReAct: Three-stage pipeline with planner, coder, and critic
"""
from __future__ import annotations

from typing import List, Dict, Any

from .config import LANGUAGE_METADATA

MAX_DOC_CHARS = 6000
MAX_ICL_EXAMPLES = 3  # Paper uses 3 ICL examples


def _trim(text: str, limit: int = MAX_DOC_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]..."


def _format_tests(tests: List[Dict[str, str]]) -> str:
    lines = ["Specification tests (stdin => stdout):"]
    for idx, case in enumerate(tests, 1):
        lines.append(
            f"{idx}.\n"
            f"Input:\n{case.get('input', '')}\n"
            f"Output:\n{case.get('output', '')}\n"
        )
    return "\n".join(lines)


def _format_icl_examples(examples: List[Dict[str, Any]]) -> str:
    chunks = []
    for idx, example in enumerate(examples[:MAX_ICL_EXAMPLES], 1):
        io_text = "\n".join(
            f"- Input: {io.get('input', '')}\n  Output: {io.get('output', '')}"
            for io in example.get("io_examples", [])
        )
        chunks.append(
            f"Example {idx}: {example.get('title', example.get('id', 'Example'))}\n"
            f"Task: {example.get('question', '')}\n"
            f"Program:\n{example.get('program', '')}\n"
            f"Sample I/O:\n{io_text}"
        )
    return "\n\n".join(chunks)


# =============================================================================
# Zero-Shot Prompts
# =============================================================================

def build_zero_shot_prompts(language_id: str, doc_text: str, problem: Dict[str, Any]) -> tuple[str, List[str]]:
    """Build prompts for zero-shot code generation."""
    language_name = LANGUAGE_METADATA[language_id]["name"]
    system_prompt = (
        f"You are an expert {language_name} programmer. "
        "Given a problem and sample tests, output ONLY valid code in this esoteric language. "
        "No explanations, no comments, no markdown. Programs must read stdin exactly as specified and "
        "write deterministic stdout that matches the expected output byte-for-byte."
        f"\n\nReference documentation:\n{_trim(doc_text)}"
    )
    user_prompt = (
        f"Problem ID: {problem['id']}\nTitle: {problem['title']}\n"
        f"Description:\n{problem['description']}\n\n{_format_tests(problem['tests'])}\n"
        "Return only the program."
    )
    return system_prompt, [user_prompt]


# =============================================================================
# Few-Shot Prompts (3 ICL examples)
# =============================================================================

def build_few_shot_prompts(
    language_id: str,
    doc_text: str,
    problem: Dict[str, Any],
    icl_examples: List[Dict[str, Any]],
) -> tuple[str, List[str]]:
    """Build prompts for few-shot code generation with 3 ICL examples."""
    system_prompt = (
        build_zero_shot_prompts(language_id, doc_text, problem)[0]
        + "\n\nHere are solved examples for reference."
    )
    examples_text = _format_icl_examples(icl_examples)
    problem_text = (
        f"Problem ID: {problem['id']}\nTitle: {problem['title']}\n"
        f"Description:\n{problem['description']}\n\n{_format_tests(problem['tests'])}\n"
        "Return only the program."
    )
    return system_prompt, [examples_text, problem_text]


# =============================================================================
# Self-Scaffolding Prompts (1 LLM call per iteration, direct interpreter feedback)
# This is the best-performing non-agentic strategy per the paper.
# =============================================================================

def build_self_scaffolding_prompt(
    language_id: str,
    doc_text: str,
    problem: Dict[str, Any],
    icl_examples: List[Dict[str, Any]] | None,
    attempt_context: str | None,
) -> tuple[str, List[str]]:
    """
    Build prompts for self-scaffolding with direct interpreter feedback.

    This regime uses a single LLM call per iteration. The model receives
    raw interpreter output (actual vs expected, error messages) and must
    self-diagnose issues without a separate critic.
    """
    system_prompt = (
        build_zero_shot_prompts(language_id, doc_text, problem)[0]
        + "\nIteratively update your program using the prior code and interpreter feedback provided."
    )
    messages: List[str] = []
    if icl_examples:
        messages.append("Reference examples:\n" + _format_icl_examples(icl_examples))
    prompt = (
        f"Problem ID: {problem['id']}\nTitle: {problem['title']}\n"
        f"Description:\n{problem['description']}\n\n{_format_tests(problem['tests'])}"
    )
    if attempt_context:
        prompt += (
            "\n\nPrevious attempt and interpreter feedback:\n"
            f"{attempt_context}"
        )
    prompt += "\nReturn only the updated program."
    messages.append(prompt)
    return system_prompt, messages


# =============================================================================
# Textual Self-Scaffolding Prompts (2 LLM calls per iteration: coder + critic)
# =============================================================================

def build_textual_self_scaffolding_coder_prompt(
    language_id: str,
    doc_text: str,
    problem: Dict[str, Any],
    icl_examples: List[Dict[str, Any]] | None,
    feedback: str | None,
    previous_code: str | None,
) -> tuple[str, List[str]]:
    """
    Build coder prompts for textual self-scaffolding.

    The coder generates code given the problem and any prior critic feedback.
    """
    system_prompt = (
        build_zero_shot_prompts(language_id, doc_text, problem)[0]
        + "\nIteratively improve your solution when feedback is provided."
    )
    messages: List[str] = []
    if icl_examples:
        messages.append("Reference examples:\n" + _format_icl_examples(icl_examples))
    prompt = (
        f"Problem ID: {problem['id']}\nTitle: {problem['title']}\n"
        f"Description:\n{problem['description']}\n\n{_format_tests(problem['tests'])}"
    )
    if previous_code:
        prompt += f"\n\nPrevious attempt:\n{previous_code}"
    if feedback:
        prompt += f"\n\nCritic feedback:\n{feedback}"
    prompt += "\nReturn only the updated program."
    messages.append(prompt)
    return system_prompt, messages


def build_textual_self_scaffolding_critic_prompt(
    language_id: str,
    problem: Dict[str, Any],
    attempt_report: str,
) -> tuple[str, List[str]]:
    """
    Build critic prompts for textual self-scaffolding.

    The critic analyzes failing code and interpreter output to provide
    natural-language debugging guidance. It cannot write code.
    """
    language_name = LANGUAGE_METADATA[language_id]["name"]
    system_prompt = (
        f"You are an expert {language_name} reviewer. "
        "Analyse the failing program and interpreter feedback. "
        "Explain issues and suggest improvements in natural language only. Do not write code."
    )
    user_prompt = (
        f"Problem ID: {problem['id']}\nTitle: {problem['title']}\n"
        f"Description:\n{problem['description']}\n\nAttempt details:\n{attempt_report}\n"
        "Provide concise debugging guidance without including any code."
    )
    return system_prompt, [user_prompt]


# =============================================================================
# ReAct Pipeline Prompts (planner + coder + critic)
# Inspired by Yao et al. (2023) "ReAct: Synergizing Reasoning and Acting"
# =============================================================================

def build_react_planner_prompt(
    language_id: str,
    doc_text: str,
    problem: Dict[str, Any],
    previous_plan: str | None = None,
    critic_feedback: str | None = None,
) -> tuple[str, List[str]]:
    """
    Build planner prompts for ReAct pipeline.

    The planner generates a high-level algorithm in pseudocode.
    """
    language_name = LANGUAGE_METADATA[language_id]["name"]
    system_prompt = (
        f"You are an algorithm designer planning solutions for {language_name} programs. "
        "Given a problem, produce a clear step-by-step pseudocode algorithm. "
        "Focus on the logical structure, not language-specific syntax. "
        "Be explicit about data structures, loop conditions, and I/O handling."
        f"\n\nTarget language documentation (for context):\n{_trim(doc_text, 3000)}"
    )
    prompt = (
        f"Problem ID: {problem['id']}\nTitle: {problem['title']}\n"
        f"Description:\n{problem['description']}\n\n{_format_tests(problem['tests'])}"
    )
    if previous_plan:
        prompt += f"\n\nPrevious plan:\n{previous_plan}"
    if critic_feedback:
        prompt += f"\n\nCritic feedback on failed implementation:\n{critic_feedback}"
        prompt += "\n\nRevise the algorithm to address the issues identified."
    prompt += "\n\nProvide a clear pseudocode algorithm."
    return system_prompt, [prompt]


def build_react_coder_prompt(
    language_id: str,
    doc_text: str,
    problem: Dict[str, Any],
    plan: str,
    icl_examples: List[Dict[str, Any]] | None = None,
) -> tuple[str, List[str]]:
    """
    Build coder prompts for ReAct pipeline.

    The coder translates the planner's pseudocode into target esoteric language.
    """
    language_name = LANGUAGE_METADATA[language_id]["name"]
    system_prompt = (
        f"You are an expert {language_name} programmer. "
        "Given a pseudocode algorithm, translate it into valid code. "
        "Output ONLY the program code, no explanations or markdown."
        f"\n\nReference documentation:\n{_trim(doc_text)}"
    )
    messages: List[str] = []
    if icl_examples:
        messages.append("Reference examples:\n" + _format_icl_examples(icl_examples))
    prompt = (
        f"Problem ID: {problem['id']}\nTitle: {problem['title']}\n"
        f"Description:\n{problem['description']}\n\n{_format_tests(problem['tests'])}\n\n"
        f"Algorithm to implement:\n{plan}\n\n"
        "Return only the program."
    )
    messages.append(prompt)
    return system_prompt, messages


def build_react_critic_prompt(
    language_id: str,
    problem: Dict[str, Any],
    plan: str,
    attempt_report: str,
) -> tuple[str, List[str]]:
    """
    Build critic prompts for ReAct pipeline.

    The critic analyzes execution failures and feeds back to the planner.
    """
    language_name = LANGUAGE_METADATA[language_id]["name"]
    system_prompt = (
        f"You are a debugging expert for {language_name} programs. "
        "Analyze the failed implementation and determine if the issue is:\n"
        "1. An algorithm/logic problem (planner should revise the approach)\n"
        "2. A translation/syntax problem (coder misimplemented the plan)\n"
        "Provide specific feedback to guide the next iteration. Do not write code."
    )
    user_prompt = (
        f"Problem ID: {problem['id']}\nTitle: {problem['title']}\n"
        f"Description:\n{problem['description']}\n\n"
        f"Planned algorithm:\n{plan}\n\n"
        f"Implementation results:\n{attempt_report}\n\n"
        "Analyze the failure and provide feedback for the planner."
    )
    return system_prompt, [user_prompt]
