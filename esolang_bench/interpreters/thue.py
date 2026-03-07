from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import List, Tuple

from .base import BaseInterpreter, ExecutionResult
from .utils import deque_from_bytes_or_str


@dataclass
class Rule:
    pattern: str
    replacement: str


class ThueInterpreter(BaseInterpreter):
    language_name = "Thue"

    def _execute(self, code: str, stdin: str | bytes | None) -> ExecutionResult:
        try:
            rules, initial_string = self._parse(code)
        except ValueError as exc:
            return ExecutionResult(
                stdout="",
                stderr=f"Thue compile error: {exc}",
                exit_code=1,
                error_type="compile_error",
            )

        stream = deque_from_bytes_or_str(stdin)
        working = initial_string
        stdout_chars: List[str] = []
        steps = 0
        max_steps = 50000

        while steps < max_steps:
            for rule in rules:
                idx = working.find(rule.pattern)
                if idx != -1:
                    if rule.replacement == "~":
                        ch = chr(stream.popleft()) if stream else ""
                        working = working[:idx] + ch + working[idx + len(rule.pattern) :]
                    elif rule.replacement.startswith("::="):
                        stdout_chars.append(rule.replacement[3:])
                        working = working[:idx] + working[idx + len(rule.pattern) :]
                    else:
                        working = working[:idx] + rule.replacement + working[idx + len(rule.pattern) :]
                    steps += 1
                    break
            else:
                break
        else:
            return ExecutionResult(
                stdout="".join(stdout_chars),
                stderr="Thue runtime error: exceeded step budget",
                exit_code=1,
                error_type="runtime_error",
            )

        return ExecutionResult(
            stdout="".join(stdout_chars),
            stderr="",
            exit_code=0,
            error_type="ok",
        )

    def _parse(self, code: str) -> Tuple[List[Rule], str]:
        lines = [line.rstrip("\n") for line in code.splitlines()]
        rules: List[Rule] = []
        initial_lines = []
        separator_seen = False
        for line in lines:
            if not line.strip():
                separator_seen = True
                continue
            if not separator_seen:
                if "::=" not in line:
                    raise ValueError(f"invalid rule line: {line}")
                pat, repl = line.split("::=", 1)
                rules.append(Rule(pat, repl))
            else:
                initial_lines.append(line)
        initial = "\n".join(initial_lines)
        if not rules:
            raise ValueError("no Thue rules provided")
        return rules, initial
