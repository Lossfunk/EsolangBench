from __future__ import annotations

import random
from typing import List, Tuple

from .base import BaseInterpreter, ExecutionResult
from .utils import InputBuffer, coerce_input


DIRECTIONS = {
    ">": (1, 0),
    "<": (-1, 0),
    "^": (0, -1),
    "v": (0, 1),
}


class Befunge98Interpreter(BaseInterpreter):
    """Reasonably complete Befunge-98 VM with tracing."""

    language_name = "Befunge-98"

    def _execute(self, code: str, stdin: str | bytes | None) -> ExecutionResult:
        try:
            self._validate_code(code)
        except ValueError as exc:
            return ExecutionResult(
                stdout="",
                stderr=f"Befunge compile error: {exc}",
                exit_code=1,
                error_type="compile_error",
            )
        grid = self._build_grid(code)
        width = len(grid[0])
        height = len(grid)
        stack: List[int] = []
        ip_x = ip_y = 0
        dx, dy = DIRECTIONS[">"]
        string_mode = False
        stdout_chars: List[str] = []
        input_stream: InputBuffer = coerce_input(stdin)
        steps = 0
        max_steps = 200000
        last_ops: List[str] = []

        def pop() -> int:
            if not stack:
                raise RuntimeError("stack underflow")
            return stack.pop()

        halted = False
        try:
            while not halted:
                command = grid[ip_y][ip_x]
                steps += 1
                last_ops.append(f"{ip_x},{ip_y}:{command}")
                if len(last_ops) > 12:
                    last_ops.pop(0)

                if string_mode and command != '"':
                    stack.append(ord(command))
                elif command in "0123456789":
                    stack.append(int(command))
                elif command == "+":
                    stack.append(pop() + pop())
                elif command == "-":
                    b, a = pop(), pop()
                    stack.append(a - b)
                elif command == "*":
                    stack.append(pop() * pop())
                elif command == "/":
                    b, a = pop(), pop()
                    if b == 0:
                        raise RuntimeError("division by zero")
                    stack.append(int(a / b))
                elif command == "%":
                    b, a = pop(), pop()
                    if b == 0:
                        raise RuntimeError("modulo by zero")
                    stack.append(a % b)
                elif command == "!":
                    stack.append(0 if pop() else 1)
                elif command == "`":
                    b, a = pop(), pop()
                    stack.append(1 if a > b else 0)
                elif command in DIRECTIONS:
                    dx, dy = DIRECTIONS[command]
                elif command == "?":
                    dx, dy = random.choice(list(DIRECTIONS.values()))
                elif command == "_":
                    dx, dy = (1, 0) if pop() == 0 else (-1, 0)
                elif command == "|":
                    dx, dy = (0, 1) if pop() == 0 else (0, -1)
                elif command == ":":
                    stack.append(stack[-1] if stack else 0)
                elif command == "\\":
                    if len(stack) < 2:
                        stack.append(0)
                    else:
                        stack[-1], stack[-2] = stack[-2], stack[-1]
                elif command == "$":
                    pop()
                elif command == ".":
                    stdout_chars.append(str(pop()))
                elif command == ",":
                    stdout_chars.append(chr(pop() % 256))
                elif command == "#":
                    ip_x = (ip_x + dx) % width
                    ip_y = (ip_y + dy) % height
                elif command == "g":
                    y = pop()
                    x = pop()
                    stack.append(ord(self._safe_get(grid, width, height, x, y)))
                elif command == "p":
                    y = pop()
                    x = pop()
                    value = pop()
                    self._safe_set(grid, width, height, x, y, chr(value % 256))
                elif command == "&":
                    number = input_stream.read_number()
                    # On EOF, push 0 per common Befunge practice for robustness
                    stack.append(0 if number is None else number)
                elif command == "~":
                    char = input_stream.read_char()
                    # On EOF, push 0 to allow loops to detect termination
                    stack.append(0 if char is None else ord(char))
                elif command == '"':
                    string_mode = not string_mode
                elif command == "'":
                    # Push next character literal
                    ip_x = (ip_x + dx) % width
                    ip_y = (ip_y + dy) % height
                    stack.append(ord(grid[ip_y][ip_x]))
                elif command == "@":
                    halted = True
                elif command == "k":
                    count = pop()
                    for _ in range(max(count, 0)):
                        ip_x = (ip_x + dx) % width
                        ip_y = (ip_y + dy) % height
                    continue
                elif command == " ":
                    pass
                else:
                    raise RuntimeError(f"unknown instruction '{command}'")

                if halted:
                    break

                if steps > max_steps:
                    raise RuntimeError("maximum instruction budget exceeded")

                ip_x = (ip_x + dx) % width
                ip_y = (ip_y + dy) % height
        except RuntimeError as exc:
            return ExecutionResult(
                stdout="".join(stdout_chars),
                stderr=f"Befunge runtime error: {exc}",
                exit_code=1,
                error_type="runtime_error",
                trace=self._trace(steps, ip_x, ip_y, dx, dy, stack, last_ops),
            )

        trace = self._trace(steps, ip_x, ip_y, dx, dy, stack, last_ops)
        return ExecutionResult(
            stdout="".join(stdout_chars),
            stderr="",
            exit_code=0,
            error_type="ok",
            trace=trace,
        )

    def _validate_code(self, code: str) -> None:
        for idx, ch in enumerate(code):
            if ord(ch) < 32 and ch not in {"\n", "\r", "\t"}:
                raise ValueError(f"invalid control character at offset {idx}")

    def _build_grid(self, code: str) -> List[List[str]]:
        lines = code.splitlines() or [""]
        width = max(1, max(len(line) for line in lines))
        grid = [list(line.ljust(width)) for line in lines]
        return grid

    def _safe_get(self, grid: List[List[str]], width: int, height: int, x: int, y: int) -> str:
        x %= width
        y %= height
        return grid[y][x]

    def _safe_set(self, grid: List[List[str]], width: int, height: int, x: int, y: int, value: str) -> None:
        x %= width
        y %= height
        grid[y][x] = value[0]

    def _trace(
        self,
        steps: int,
        x: int,
        y: int,
        dx: int,
        dy: int,
        stack: List[int],
        last_ops: List[str],
    ) -> dict:
        return {
            "steps": steps,
            "ip": {"x": x, "y": y, "direction": {"dx": dx, "dy": dy}},
            "stack_depth": len(stack),
            "stack_preview": stack[-8:],
            "last_ops": last_ops[-10:],
        }
