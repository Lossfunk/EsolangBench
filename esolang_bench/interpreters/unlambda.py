from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Tuple

from .base import BaseInterpreter, ExecutionResult
from .utils import InputBuffer, coerce_input


class Function:
    def __init__(self, fn: Callable[["Function"], "Function"]):
        self.fn = fn

    def __call__(self, arg: "Function") -> "Function":
        return self.fn(arg)


@dataclass
class EvalEnv:
    stdout: List[str]
    input_stream: InputBuffer


class UnlambdaInterpreter(BaseInterpreter):
    """Minimal-yet-useful Unlambda interpreter covering core combinators."""

    language_name = "Unlambda"

    def _execute(self, code: str, stdin: str | bytes | None) -> ExecutionResult:
        try:
            expr = self._parse(code)
        except ValueError as exc:
            return ExecutionResult(
                stdout="",
                stderr=f"Unlambda compile error: {exc}",
                exit_code=1,
                error_type="compile_error",
            )

        env = EvalEnv(stdout=[], input_stream=coerce_input(stdin))
        try:
            self._evaluate(expr, env)
        except RuntimeError as exc:
            return ExecutionResult(
                stdout="".join(env.stdout),
                stderr=f"Unlambda runtime error: {exc}",
                exit_code=1,
                error_type="runtime_error",
            )

        return ExecutionResult(
            stdout="".join(env.stdout),
            stderr="",
            exit_code=0,
            error_type="ok",
            trace={"steps": len(env.stdout)},
        )

    def _parse(self, code: str):
        cleaned = []
        commenting = False
        after_dot = False
        for ch in code:
            if commenting:
                if ch in "\r\n":
                    commenting = False
                continue
            if ch == "#":
                commenting = True
                continue
            # Preserve whitespace immediately after a dot (for printing spaces)
            if after_dot:
                cleaned.append(ch)
                after_dot = False
                continue
            if ch == ".":
                cleaned.append(ch)
                after_dot = True
                continue
            if ch in {" ", "\t", "\r", "\n"}:
                continue
            cleaned.append(ch)
        tokens = "".join(cleaned)
        if not tokens:
            raise ValueError("empty Unlambda program")
        expr, idx = self._parse_expr(tokens, 0)
        if idx != len(tokens):
            raise ValueError("unexpected trailing tokens")
        return expr

    def _parse_expr(self, tokens: str, idx: int):
        if idx >= len(tokens):
            raise ValueError("unexpected end of program")
        ch = tokens[idx]
        if ch == "`":
            func, idx = self._parse_expr(tokens, idx + 1)
            arg, idx = self._parse_expr(tokens, idx)
            return ("apply", func, arg), idx
        if ch == ".":
            if idx + 1 >= len(tokens):
                raise ValueError("'.' missing character")
            literal = tokens[idx + 1]
            return ("dot", literal), idx + 2
        if ch in {"s", "k", "i", "r"}:
            return ("symbol", ch), idx + 1
        raise ValueError(f"unsupported token '{ch}'")

    def _evaluate(self, node, env: EvalEnv) -> Function:
        kind = node[0]
        if kind == "symbol":
            return self._builtin(node[1], env)
        if kind == "dot":
            char = "\n" if node[1] == "n" else node[1]

            def printer(arg: Function) -> Function:
                env.stdout.append(char)
                return arg

            return Function(printer)
        if kind == "apply":
            func = self._evaluate(node[1], env)
            arg = self._evaluate(node[2], env)
            return func(arg)
        raise RuntimeError("unknown AST node")

    def _builtin(self, symbol: str, env: EvalEnv) -> Function:
        if symbol == "s":
            return Function(lambda x: Function(lambda y: Function(lambda z: x(z)(y(z)))))
        if symbol == "k":
            return Function(lambda x: Function(lambda y: x))
        if symbol == "i":
            return Function(lambda x: x)
        if symbol == "r":
            def reader(x: Function) -> Function:
                char = env.input_stream.read_char()
                if char is None:
                    raise RuntimeError("character input exhausted")
                env.stdout.append(char)
                return x

            return Function(reader)
        raise RuntimeError(f"unsupported builtin '{symbol}'")
