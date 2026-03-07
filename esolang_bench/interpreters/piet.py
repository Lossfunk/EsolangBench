from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from .base import BaseInterpreter, ExecutionResult
from .utils import InputBuffer, coerce_input

Color = Union[Tuple[int, int], str]  # (hue, light) or "white"/"black"


PIET_COLORS: Dict[str, Color] = {
    "light_red": (0, 0),
    "red": (0, 1),
    "dark_red": (0, 2),
    "light_yellow": (1, 0),
    "yellow": (1, 1),
    "dark_yellow": (1, 2),
    "light_green": (2, 0),
    "green": (2, 1),
    "dark_green": (2, 2),
    "light_cyan": (3, 0),
    "cyan": (3, 1),
    "dark_cyan": (3, 2),
    "light_blue": (4, 0),
    "blue": (4, 1),
    "dark_blue": (4, 2),
    "light_magenta": (5, 0),
    "magenta": (5, 1),
    "dark_magenta": (5, 2),
    "white": "white",
    "black": "black",
}


SHORTCUTS = {
    "lr": "light_red",
    "mr": "red",
    "dr": "dark_red",
    "ly": "light_yellow",
    "y": "yellow",
    "dy": "dark_yellow",
    "lg": "light_green",
    "g": "green",
    "dg": "dark_green",
    "lc": "light_cyan",
    "c": "cyan",
    "dc": "dark_cyan",
    "lb": "light_blue",
    "b": "blue",
    "db": "dark_blue",
    "lm": "light_magenta",
    "m": "magenta",
    "dm": "dark_magenta",
}


COMMAND_TABLE = [
    ["noop", "push", "pop", "add", "sub", "mul"],
    ["div", "mod", "not", "greater", "pointer", "switch"],
    ["duplicate", "roll", "in_number", "in_char", "out_number", "out_char"],
]


@dataclass
class PietBlock:
    ident: int
    color: Color
    cells: List[Tuple[int, int]]

    @property
    def size(self) -> int:
        return len(self.cells)


class PietProgram:
    def __init__(self, grid: List[List[Color]]):
        self.grid = grid
        self.height = len(grid)
        self.width = len(grid[0]) if self.height else 0
        self.block_ids: List[List[int]] = [[-1] * self.width for _ in range(self.height)]
        self.blocks: List[PietBlock] = []
        self._build_blocks()
        self.start = self._find_start()

    def _build_blocks(self) -> None:
        ident = 0
        for y in range(self.height):
            for x in range(self.width):
                if self.block_ids[y][x] != -1:
                    continue
                color = self.grid[y][x]
                if color == "black":
                    self.block_ids[y][x] = -2
                    continue
                cells = self._collect_block(x, y, color)
                block = PietBlock(ident, color, cells)
                for cx, cy in cells:
                    self.block_ids[cy][cx] = ident
                self.blocks.append(block)
                ident += 1

    def _collect_block(self, x: int, y: int, color: Color) -> List[Tuple[int, int]]:
        frontier = [(x, y)]
        cells: List[Tuple[int, int]] = []
        self.block_ids[y][x] = -3
        while frontier:
            cx, cy = frontier.pop()
            cells.append((cx, cy))
            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if self.block_ids[ny][nx] == -1 and self.grid[ny][nx] == color:
                        self.block_ids[ny][nx] = -3
                        frontier.append((nx, ny))
        return cells

    def _find_start(self) -> Tuple[int, int]:
        for y in range(self.height):
            for x in range(self.width):
                color = self.grid[y][x]
                if color not in {"white", "black"}:
                    return (x, y)
        raise ValueError("program does not contain a starting colored block")

    def color_at(self, x: int, y: int) -> Color:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return "black"
        return self.grid[y][x]

    def block_at(self, x: int, y: int) -> Optional[PietBlock]:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return None
        ident = self.block_ids[y][x]
        if ident < 0:
            return None
        return self.blocks[ident]


class PietInterpreter(BaseInterpreter):
    language_name = "Piet"

    def _execute(self, code: str, stdin: str | bytes | None) -> ExecutionResult:
        try:
            program = self._parse(code)
        except ValueError as exc:
            return ExecutionResult(
                stdout="",
                stderr=f"Piet compile error: {exc}",
                exit_code=1,
                error_type="compile_error",
            )

        stack: List[int] = []
        stdout_chars: List[str] = []
        input_stream: InputBuffer = coerce_input(stdin)
        dp = (1, 0)
        cc = "left"
        position = program.start
        steps = 0

        last_command = None
        history: List[str] = []

        while True:
            block = program.block_at(*position)
            if block is None or block.color in {"white", "black"}:
                next_move = self._advance(program, position, dp, cc)
            else:
                next_move = self._advance(program, position, dp, cc)
            if next_move is None:
                break
            position, dp, cc, from_block, to_block = next_move
            if to_block.color == "white":
                continue
            command = self._command_for_transition(from_block.color, to_block.color)
            if command == "noop":
                continue
            last_command = command
            history.append(command)
            if len(history) > 10:
                history.pop(0)
            steps += 1
            try:
                dp, cc = self._execute_command(
                    command, to_block.size, stack, stdout_chars, input_stream, dp, cc
                )
            except RuntimeError as exc:
                return ExecutionResult(
                    stdout="".join(stdout_chars),
                    stderr=f"Piet runtime error: {exc}",
                    exit_code=1,
                    error_type="runtime_error",
                    trace=self._trace(steps, position, dp, cc, stack, last_command, history),
                )

        trace = self._trace(steps, position, dp, cc, stack, last_command, history)
        return ExecutionResult(
            stdout="".join(stdout_chars),
            stderr="",
            exit_code=0,
            error_type="ok",
            trace=trace,
        )

    def _parse(self, code: str) -> PietProgram:
        grid: List[List[Color]] = []
        for line in code.strip().splitlines():
            tokens = [token for token in line.strip().split(" ") if token]
            if not tokens:
                continue
            row: List[Color] = []
            for token in tokens:
                key = token.lower()
                if key in SHORTCUTS:
                    key = SHORTCUTS[key]
                if key not in PIET_COLORS:
                    raise ValueError(f"unknown Piet color token '{token}'")
                row.append(PIET_COLORS[key])
            grid.append(row)
        if not grid:
            raise ValueError("empty Piet program")

        width = max(len(row) for row in grid)
        normalized = [row + ["white"] * (width - len(row)) for row in grid]
        return PietProgram(normalized)

    def _advance(
        self,
        program: PietProgram,
        position: Tuple[int, int],
        dp: Tuple[int, int],
        cc: str,
    ) -> Optional[Tuple[Tuple[int, int], Tuple[int, int], str, PietBlock, PietBlock]]:
        block = program.block_at(*position)
        if block is None:
            return None
        attempts = 0
        current_dp = dp
        current_cc = cc
        while attempts < 8:
            exit_cell = self._choose_exit(block, current_dp, current_cc)
            nx = exit_cell[0] + current_dp[0]
            ny = exit_cell[1] + current_dp[1]
            color = program.color_at(nx, ny)
            if color == "black":
                attempts += 1
                current_cc = self._toggle_cc(current_cc)
                current_dp = self._rotate_dp(current_dp)
                continue
            if color == "white":
                traversal = self._traverse_white(program, nx, ny, current_dp)
                if traversal is None:
                    attempts += 1
                    current_cc = self._toggle_cc(current_cc)
                    current_dp = self._rotate_dp(current_dp)
                    continue
                nx, ny = traversal
                color = program.color_at(nx, ny)
            next_block = program.block_at(nx, ny)
            if next_block is None:
                return None
            return ((nx, ny), current_dp, current_cc, block, next_block)
        return None

    def _choose_exit(self, block: PietBlock, dp: Tuple[int, int], cc: str) -> Tuple[int, int]:
        cells = block.cells
        if dp == (1, 0):
            target_x = max(x for x, _ in cells)
            candidates = [(x, y) for x, y in cells if x == target_x]
            candidates.sort(key=lambda c: c[1], reverse=(cc == "right"))
        elif dp == (-1, 0):
            target_x = min(x for x, _ in cells)
            candidates = [(x, y) for x, y in cells if x == target_x]
            candidates.sort(key=lambda c: c[1], reverse=(cc == "left"))
        elif dp == (0, 1):
            target_y = max(y for _, y in cells)
            candidates = [(x, y) for x, y in cells if y == target_y]
            candidates.sort(key=lambda c: c[0], reverse=(cc == "right"))
        else:  # dp == (0, -1)
            target_y = min(y for _, y in cells)
            candidates = [(x, y) for x, y in cells if y == target_y]
            candidates.sort(key=lambda c: c[0], reverse=(cc == "left"))
        return candidates[0]

    def _traverse_white(
        self,
        program: PietProgram,
        x: int,
        y: int,
        dp: Tuple[int, int],
    ) -> Optional[Tuple[int, int]]:
        nx, ny = x, y
        while True:
            color = program.color_at(nx, ny)
            if color == "white":
                nx += dp[0]
                ny += dp[1]
                continue
            if color == "black":
                return None
            return (nx, ny)

    def _command_for_transition(self, from_color: Color, to_color: Color) -> str:
        if isinstance(from_color, str) or isinstance(to_color, str):
            return "noop"
        hue_shift = (to_color[0] - from_color[0]) % 6
        light_shift = (to_color[1] - from_color[1]) % 3
        return COMMAND_TABLE[light_shift][hue_shift]

    def _execute_command(
        self,
        command: str,
        block_size: int,
        stack: List[int],
        stdout_chars: List[str],
        input_stream: InputBuffer,
        dp: Tuple[int, int],
        cc: str,
    ) -> Tuple[Tuple[int, int], str]:
        def pop() -> int:
            if not stack:
                raise RuntimeError("stack underflow")
            return stack.pop()

        if command == "push":
            stack.append(block_size)
        elif command == "pop":
            pop()
        elif command == "add":
            a = pop()
            b = pop()
            stack.append(b + a)
        elif command == "sub":
            a = pop()
            b = pop()
            stack.append(b - a)
        elif command == "mul":
            stack.append(pop() * pop())
        elif command == "div":
            a = pop()
            b = pop()
            if a == 0:
                raise RuntimeError("division by zero")
            stack.append(b // a)
        elif command == "mod":
            a = pop()
            b = pop()
            if a == 0:
                raise RuntimeError("modulo by zero")
            stack.append(b % a)
        elif command == "not":
            stack.append(1 if pop() == 0 else 0)
        elif command == "greater":
            a = pop()
            b = pop()
            stack.append(1 if b > a else 0)
        elif command == "pointer":
            turns = pop()
            dp = self._rotate_dp(dp, turns)
        elif command == "switch":
            flips = pop()
            if flips % 2:
                cc = self._toggle_cc(cc)
        elif command == "duplicate":
            if not stack:
                raise RuntimeError("stack underflow")
            stack.append(stack[-1])
        elif command == "roll":
            rolls = pop()
            depth = pop()
            if depth <= 0 or depth > len(stack):
                raise RuntimeError("invalid roll depth")
            depth_slice = stack[-depth:]
            rolls = rolls % depth
            if rolls:
                depth_slice = depth_slice[-rolls:] + depth_slice[:-rolls]
            stack[-depth:] = depth_slice
        elif command == "in_number":
            number = input_stream.read_number()
            if number is None:
                raise RuntimeError("numeric input exhausted")
            stack.append(number)
        elif command == "in_char":
            char = input_stream.read_char()
            if char is None:
                raise RuntimeError("character input exhausted")
            stack.append(ord(char))
        elif command == "out_number":
            stdout_chars.append(str(pop()))
        elif command == "out_char":
            stdout_chars.append(chr(pop() % 256))
        return dp, cc

    def _rotate_dp(self, dp: Tuple[int, int], turns: int = 1) -> Tuple[int, int]:
        dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        idx = dirs.index(dp)
        return dirs[(idx + turns) % 4]

    def _toggle_cc(self, cc: str) -> str:
        return "right" if cc == "left" else "left"

    def _trace(
        self,
        steps: int,
        position: Tuple[int, int],
        dp: Tuple[int, int],
        cc: str,
        stack: List[int],
        last_command: Optional[str],
        history: List[str],
    ) -> dict:
        return {
            "steps": steps,
            "position": {"x": position[0], "y": position[1]},
            "dp": dp,
            "cc": cc,
            "stack_depth": len(stack),
            "stack_preview": stack[-8:],
            "last_command": last_command,
            "history": history[-8:],
        }
