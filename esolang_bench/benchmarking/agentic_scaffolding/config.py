from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolProfile:
    key: str
    description: str
    share_interpreter_feedback: bool
    share_tool_feedback: bool
    no_feedback_message: str


TOOL_PROFILES: dict[str, ToolProfile] = {
    "full_access": ToolProfile(
        key="full_access",
        description=(
            "You can call a local esoteric-language interpreter, inspect stderr/stdout, "
            "run lightweight analyses, and reason step-by-step before responding."
        ),
        share_interpreter_feedback=True,
        share_tool_feedback=True,
        no_feedback_message="Interpreter available. Use it to validate future attempts.",
    ),
    "blind_no_tools": ToolProfile(
        key="blind_no_tools",
        description=(
            "You must reason purely from the specification. You cannot execute code or "
            "use any auxiliary tools. Produce your best final answer directly."
        ),
        share_interpreter_feedback=False,
        share_tool_feedback=False,
        no_feedback_message="No tools or interpreter feedback is available for this regime.",
    ),
    "interpreter_only": ToolProfile(
        key="interpreter_only",
        description=(
            "You may run the local interpreter to check program behavior but you have no other "
            "external tools. Use interpreter feedback to iteratively improve the solution."
        ),
        share_interpreter_feedback=True,
        share_tool_feedback=False,
        no_feedback_message="Interpreter output unavailable this round.",
    ),
}
