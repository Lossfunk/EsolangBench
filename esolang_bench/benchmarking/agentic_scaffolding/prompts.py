from __future__ import annotations

from typing import Any, Dict, List, Optional

from esolang_bench.benchmarking.config import LANGUAGE_METADATA
from .config import ToolProfile

MAX_DOC_CHARS = 6000
MAX_ICL_EXAMPLES = 2


def _trim_doc(text: str) -> str:
    if len(text) <= MAX_DOC_CHARS:
        return text
    return text[:MAX_DOC_CHARS] + "\n...[truncated]..."


def _format_tests(tests: List[Dict[str, str]]) -> str:
    chunks = ["Specification tests (stdin => stdout):"]
    for idx, case in enumerate(tests, 1):
        chunks.append(
            f"{idx}.\nInput:\n{case.get('input', '')}\nOutput:\n{case.get('output', '')}\n"
        )
    return "\n".join(chunks)


def _format_icl(examples: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for idx, example in enumerate(examples[:MAX_ICL_EXAMPLES], 1):
        ios = "\n".join(
            f"- Input: {io.get('input', '')}\n  Output: {io.get('output', '')}"
            for io in example.get("io_examples", [])
        )
        lines.append(
            f"Example {idx}: {example.get('title', example.get('id', 'Example'))}\n"
            f"Task: {example.get('question', '')}\n"
            f"Program:\n{example.get('program', '')}\n"
            f"Sample I/O:\n{ios}"
        )
    return "\n\n".join(lines)


def build_agentic_prompts(
    language_id: str,
    doc_text: str,
    problem: Dict[str, Any],
    icl_examples: Optional[List[Dict[str, Any]]],
    profile: ToolProfile,
    attempt_feedback: Optional[str],
    previous_code: Optional[str],
) -> tuple[str, List[str]]:
    language_name = LANGUAGE_METADATA[language_id]["name"]
    system_prompt = (
        f"You are GPT-5 Codex / Claude Code style agent coding expert for {language_name}. "
        f"Available tooling: {profile.description} "
        "Always return ONLY esoteric language code without Markdown fences. "
        f"\n\nReference documentation:\n{_trim_doc(doc_text)}"
    )
    messages: List[str] = []
    if icl_examples:
        messages.append("Reference programs:\n" + _format_icl(icl_examples))
    user_prompt = (
        f"Problem ID: {problem['id']}\nTitle: {problem['title']}\n"
        f"Description:\n{problem['description']}\n\n{_format_tests(problem['tests'])}\n"
        "Reason carefully, then output only the final program."
    )
    if previous_code:
        user_prompt += f"\n\nPrevious attempt:\n{previous_code}"
    if attempt_feedback:
        user_prompt += f"\n\nTool feedback:\n{attempt_feedback}"
    messages.append(user_prompt)
    return system_prompt, messages


def format_feedback_from_tests(tests: List[Dict[str, Any]]) -> str:
    if not tests:
        return "No interpreter output captured."
    lines = ["Interpreter feedback:"]
    for idx, test in enumerate(tests, 1):
        lines.append(
            f"Test {idx} :: input={test.get('input', '')}\n"
            f"Expected: {test.get('expected_output', '')}\n"
            f"Actual: {test.get('actual_output', '')}\n"
            f"Error: {test.get('error_type', '')}\n"
            f"stderr: {test.get('stderr', '')}\n"
        )
    return "\n".join(lines)
