from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .base import BaseInterpreter, ExecutionResult
from .utils import deque_from_bytes_or_str


class BrainfuckInterpreter(BaseInterpreter):
    """Straightforward Brainfuck interpreter with helpful tracing."""

    language_name = "Brainfuck"

    def _execute(self, code: str, stdin: str | bytes | None) -> ExecutionResult:
        program = [ch for ch in code if ch in "+-<>.,[]"]
        try:
            bracket_map = self._build_bracket_map(program)
        except ValueError as exc:
            return ExecutionResult(
                stdout="",
                stderr=f"Brainfuck compile error: {exc}",
                exit_code=1,
                error_type="compile_error",
            )

        tape: List[int] = [0] * 1
        pointer = 0
        pc = 0
        stdout_chars: List[str] = []
        input_queue = deque_from_bytes_or_str(stdin)
        steps = 0
        max_pointer = 0
        last_ops: List[str] = []

        while pc < len(program):
            op = program[pc]
            steps += 1
            last_ops.append(f"{pc}:{op}")
            if len(last_ops) > 12:
                last_ops.pop(0)

            if op == ">":
                pointer += 1
                if pointer == len(tape):
                    tape.append(0)
                max_pointer = max(max_pointer, pointer)
            elif op == "<":
                pointer -= 1
                if pointer < 0:
                    return ExecutionResult(
                        stdout="".join(stdout_chars),
                        stderr="Brainfuck runtime error: pointer moved below zero",
                        exit_code=1,
                        error_type="runtime_error",
                        trace=self._trace(steps, pointer, tape, last_ops),
                    )
            elif op == "+":
                tape[pointer] = (tape[pointer] + 1) % 256
            elif op == "-":
                tape[pointer] = (tape[pointer] - 1) % 256
            elif op == ".":
                stdout_chars.append(chr(tape[pointer]))
            elif op == ",":
                tape[pointer] = input_queue.popleft() if input_queue else 0
            elif op == "[":
                if tape[pointer] == 0:
                    pc = bracket_map[pc]
            elif op == "]":
                if tape[pointer] != 0:
                    pc = bracket_map[pc]

            pc += 1

        trace = {
            "steps": steps,
            "pointer": pointer,
            "max_pointer": max_pointer,
            "tape_preview": tape[:16],
            "last_ops": last_ops,
        }
        return ExecutionResult(
            stdout="".join(stdout_chars),
            stderr="",
            exit_code=0,
            error_type="ok",
            trace=trace,
        )

    def _build_bracket_map(self, program: List[str]) -> Dict[int, int]:
        stack: List[int] = []
        bracket_map: Dict[int, int] = {}
        for idx, ch in enumerate(program):
            if ch == "[":
                stack.append(idx)
            elif ch == "]":
                if not stack:
                    raise ValueError(f"unmatched ']' at position {idx}")
                start = stack.pop()
                bracket_map[start] = idx
                bracket_map[idx] = start
        if stack:
            start = stack[-1]
            raise ValueError(f"unmatched '[' at position {start}")
        return bracket_map

    def _trace(self, steps: int, pointer: int, tape: List[int], ops: List[str]) -> Dict[str, object]:
        return {
            "steps": steps,
            "pointer": pointer,
            "tape_preview": tape[:16],
            "last_ops": ops[-8:],
        }
