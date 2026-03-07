from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .base import BaseInterpreter, ExecutionResult
from .utils import InputBuffer, coerce_input


Symbol = str


@dataclass
class WSInstruction:
    op: str
    argument: Optional[int | str]
    position: int


class WhitespaceInterpreter(BaseInterpreter):
    """Implements a useful subset of the official Whitespace specification."""

    language_name = "Whitespace"

    def _execute(self, code: str, stdin: str | bytes | None) -> ExecutionResult:
        cleaned = "".join(ch for ch in code if ch in " \t\n")
        try:
            instructions, labels = self._compile(cleaned)
        except ValueError as exc:
            return ExecutionResult(
                stdout="",
                stderr=f"Whitespace compile error: {exc}",
                exit_code=1,
                error_type="compile_error",
            )

        stack: List[int] = []
        heap: Dict[int, int] = {}
        call_stack: List[int] = []
        ip = 0
        stdout_chars: List[str] = []
        input_stream: InputBuffer = coerce_input(stdin)
        steps = 0

        while ip < len(instructions):
            ins = instructions[ip]
            steps += 1
            try:
                jump = self._execute_instruction(
                    ins, stack, heap, call_stack, stdout_chars, input_stream, labels, ip + 1
                )
            except RuntimeError as exc:
                return ExecutionResult(
                    stdout="".join(stdout_chars),
                    stderr=f"Whitespace runtime error: {exc}",
                    exit_code=1,
                    error_type="runtime_error",
                    trace=self._trace(steps, ip, stack),
                )
            if jump is None:
                ip += 1
            elif jump == -1:
                break
            else:
                ip = jump

        trace = self._trace(steps, ip, stack)
        return ExecutionResult(
            stdout="".join(stdout_chars),
            stderr="",
            exit_code=0,
            error_type="ok",
            trace=trace,
        )

    def _compile(self, cleaned: str) -> tuple[list[WSInstruction], Dict[str, int]]:
        idx = 0
        instructions: List[WSInstruction] = []
        labels: Dict[str, int] = {}

        def need_more() -> None:
            raise ValueError("unexpected end of program")

        while idx < len(cleaned):
            symbol = cleaned[idx]
            idx += 1
            if symbol == " ":
                if idx >= len(cleaned):
                    need_more()
                second = cleaned[idx]
                idx += 1
                if second == " ":
                    number, idx = self._parse_number(cleaned, idx)
                    instructions.append(WSInstruction("push", number, len(instructions)))
                elif second == "\t":
                    if idx >= len(cleaned):
                        need_more()
                    third = cleaned[idx]
                    idx += 1
                    if third == " ":
                        instructions.append(WSInstruction("dup", None, len(instructions)))
                    elif third == "\t":
                        instructions.append(WSInstruction("swap", None, len(instructions)))
                    elif third == "\n":
                        instructions.append(WSInstruction("discard", None, len(instructions)))
                    else:
                        raise ValueError("invalid stack manipulation command")
                elif second == "\n":
                    if idx >= len(cleaned):
                        need_more()
                    third = cleaned[idx]
                    idx += 1
                    if third == " ":
                        number, idx = self._parse_number(cleaned, idx)
                        instructions.append(WSInstruction("copy", number, len(instructions)))
                    elif third == "\t":
                        number, idx = self._parse_number(cleaned, idx)
                        instructions.append(WSInstruction("slide", number, len(instructions)))
                    else:
                        raise ValueError("invalid stack manipulation command")
                else:
                    raise ValueError("unknown stack manipulation instruction")
            elif symbol == "\t":
                if idx >= len(cleaned):
                    need_more()
                block = cleaned[idx]
                idx += 1
                if block == " ":
                    if idx + 1 >= len(cleaned):
                        need_more()
                    third = cleaned[idx]
                    fourth = cleaned[idx + 1]
                    idx += 2
                    pattern = third + fourth
                    mapping = {
                        "  ": "add",
                        " \t": "sub",
                        " \n": "mul",
                        "\t ": "div",
                        "\t\t": "mod",
                    }
                    if pattern not in mapping:
                        raise ValueError("invalid arithmetic opcode")
                    instructions.append(WSInstruction(mapping[pattern], None, len(instructions)))
                elif block == "\t":
                    if idx >= len(cleaned):
                        need_more()
                    third = cleaned[idx]
                    idx += 1
                    if third == " ":
                        instructions.append(WSInstruction("store", None, len(instructions)))
                    elif third == "\t":
                        instructions.append(WSInstruction("retrieve", None, len(instructions)))
                    else:
                        raise ValueError("invalid heap command")
                elif block == "\n":
                    if idx + 1 >= len(cleaned):
                        need_more()
                    third = cleaned[idx]
                    fourth = cleaned[idx + 1]
                    idx += 2
                    mapping = {
                        "  ": "print_char",
                        " \t": "print_number",
                        "\t ": "read_char",
                        "\t\t": "read_number",
                    }
                    if third + fourth not in mapping:
                        raise ValueError("invalid IO opcode")
                    instructions.append(WSInstruction(mapping[third + fourth], None, len(instructions)))
                else:
                    raise ValueError("invalid \\t instruction group")
            elif symbol == "\n":
                if idx >= len(cleaned):
                    need_more()
                block = cleaned[idx]
                idx += 1
                if block == " ":
                    if idx >= len(cleaned):
                        need_more()
                    third = cleaned[idx]
                    idx += 1
                    label, idx = self._parse_label(cleaned, idx)
                    if third == " ":
                        labels[label] = len(instructions)
                        instructions.append(WSInstruction("label", label, len(instructions)))
                    elif third == "\t":
                        instructions.append(WSInstruction("call", label, len(instructions)))
                    elif third == "\n":
                        instructions.append(WSInstruction("jump", label, len(instructions)))
                    else:
                        raise ValueError("invalid flow control opcode")
                elif block == "\t":
                    if idx >= len(cleaned):
                        need_more()
                    third = cleaned[idx]
                    idx += 1
                    if third in {" ", "\t"}:
                        label, idx = self._parse_label(cleaned, idx)
                        if third == " ":
                            instructions.append(WSInstruction("jump_zero", label, len(instructions)))
                        else:
                            instructions.append(WSInstruction("jump_negative", label, len(instructions)))
                    elif third == "\n":
                        instructions.append(WSInstruction("return", None, len(instructions)))
                    else:
                        raise ValueError("invalid conditional command")
                elif block == "\n":
                    if idx >= len(cleaned):
                        need_more()
                    third = cleaned[idx]
                    idx += 1
                    if third == "\n":
                        instructions.append(WSInstruction("end", None, len(instructions)))
                    else:
                        raise ValueError("invalid flow terminator")
                else:
                    raise ValueError("invalid flow command")
            else:
                continue

        # Validate label references
        for ins in instructions:
            if ins.op in {"call", "jump", "jump_zero", "jump_negative"}:
                if not isinstance(ins.argument, str) or ins.argument not in labels:
                    raise ValueError(f"undefined label used by {ins.op}")
        return instructions, labels

    def _parse_number(self, cleaned: str, idx: int) -> tuple[int, int]:
        if idx >= len(cleaned):
            raise ValueError("expected sign after push instruction")
        sign_char = cleaned[idx]
        if sign_char not in " \t":
            raise ValueError("invalid number literal")
        sign = 1 if sign_char == " " else -1
        idx += 1

        bits: List[str] = []
        while idx < len(cleaned) and cleaned[idx] != "\n":
            if cleaned[idx] not in " \t":
                raise ValueError("invalid digit in number literal")
            bits.append("0" if cleaned[idx] == " " else "1")
            idx += 1
        if idx >= len(cleaned) or cleaned[idx] != "\n":
            raise ValueError("number literal missing terminator")
        idx += 1
        value = int("0" + "".join(bits), 2) if bits else 0
        return sign * value, idx

    def _parse_label(self, cleaned: str, idx: int) -> tuple[str, int]:
        chars: List[str] = []
        while idx < len(cleaned) and cleaned[idx] != "\n":
            if cleaned[idx] not in " \t":
                raise ValueError("invalid character in label")
            chars.append(cleaned[idx])
            idx += 1
        if idx >= len(cleaned) or cleaned[idx] != "\n":
            raise ValueError("label missing terminator")
        idx += 1
        return "".join(chars) or "_", idx

    def _execute_instruction(
        self,
        ins: WSInstruction,
        stack: List[int],
        heap: Dict[int, int],
        call_stack: List[int],
        stdout_chars: List[str],
        input_stream: InputBuffer,
        labels: Dict[str, int],
        next_ip: int,
    ) -> Optional[int]:
        op = ins.op
        arg = ins.argument

        def pop() -> int:
            if not stack:
                raise RuntimeError("stack underflow")
            return stack.pop()

        if op == "push":
            stack.append(int(arg))
        elif op == "dup":
            if not stack:
                raise RuntimeError("stack underflow")
            stack.append(stack[-1])
        elif op == "swap":
            if len(stack) < 2:
                raise RuntimeError("stack underflow")
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif op == "discard":
            pop()
        elif op == "copy":
            index = int(arg)
            if index < 0 or index >= len(stack):
                raise RuntimeError("invalid copy distance")
            stack.append(stack[-1 - index])
        elif op == "slide":
            count = int(arg)
            if count < 0 or count >= len(stack):
                raise RuntimeError("slide exceeds stack height")
            top = stack.pop()
            del stack[-count:]
            stack.append(top)
        elif op in {"add", "sub", "mul", "div", "mod"}:
            b = pop()
            a = pop()
            if op == "add":
                stack.append(a + b)
            elif op == "sub":
                stack.append(a - b)
            elif op == "mul":
                stack.append(a * b)
            elif op == "div":
                if b == 0:
                    raise RuntimeError("division by zero")
                stack.append(int(a / b))
            else:  # mod
                if b == 0:
                    raise RuntimeError("modulo by zero")
                stack.append(a % b)
        elif op == "store":
            value = pop()
            address = pop()
            heap[address] = value
        elif op == "retrieve":
            address = pop()
            if address not in heap:
                raise RuntimeError("heap read from unset address")
            stack.append(heap[address])
        elif op == "label":
            return None
        elif op == "call":
            call_stack.append(next_ip)
            return labels[str(arg)]
        elif op == "jump":
            return labels[str(arg)]
        elif op == "jump_zero":
            value = pop()
            if value == 0:
                return labels[str(arg)]
        elif op == "jump_negative":
            value = pop()
            if value < 0:
                return labels[str(arg)]
        elif op == "return":
            if not call_stack:
                raise RuntimeError("call stack underflow")
            return call_stack.pop()
        elif op == "end":
            return -1
        elif op == "print_char":
            value = pop()
            stdout_chars.append(chr(value % 256))
        elif op == "print_number":
            value = pop()
            stdout_chars.append(str(value))
        elif op == "read_char":
            char = input_stream.read_char()
            if char is None:
                stack.append(-1)
            else:
                heap[pop()] = ord(char)
        elif op == "read_number":
            number = input_stream.read_number()
            heap[pop()] = number if number is not None else -1
        else:
            raise RuntimeError(f"unsupported opcode {op}")
        return None

    def _trace(self, steps: int, ip: int, stack: List[int]) -> Dict[str, object]:
        return {
            "steps": steps,
            "ip": ip,
            "stack_depth": len(stack),
            "stack_preview": stack[-8:],
        }
