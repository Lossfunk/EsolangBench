from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

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
    current_char: Optional[str] = None  # set by `@`, tested by `?x`, emitted by `|`


class UnlambdaInterpreter(BaseInterpreter):
    """Unlambda interpreter covering the canonical combinators (`s`, `k`, `i`,
    `.x`, `r`, `v`) plus the input/output character primitives `@`, `?x`, `|`.
    The output combinator `r` is the spec-correct shorthand for printing a
    newline (equivalent to `.<newline>`); `@` reads the next character from
    stdin into a current-character register; `?x` tests the current character
    against literal `x`; `|` re-emits the current character.
    """

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

    # ------------------------------------------------------------------ parsing

    def _parse(self, code: str):
        cleaned: List[str] = []
        commenting = False
        consume_next_literal = False  # for `.x` and `?x`
        for ch in code:
            if commenting:
                if ch in "\r\n":
                    commenting = False
                continue
            if ch == "#":
                commenting = True
                continue
            if consume_next_literal:
                cleaned.append(ch)
                consume_next_literal = False
                continue
            if ch in {".", "?"}:
                cleaned.append(ch)
                consume_next_literal = True
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
        if ch == "?":
            if idx + 1 >= len(tokens):
                raise ValueError("'?' missing character")
            literal = tokens[idx + 1]
            return ("query", literal), idx + 2
        if ch in {"s", "k", "i", "r", "v", "@", "|"}:
            return ("symbol", ch), idx + 1
        raise ValueError(f"unsupported token '{ch}'")

    # --------------------------------------------------------------- evaluation

    def _evaluate(self, node, env: EvalEnv) -> Function:
        kind = node[0]
        if kind == "symbol":
            return self._builtin(node[1], env)
        if kind == "dot":
            char = node[1]

            def printer(arg: Function) -> Function:
                env.stdout.append(char)
                return arg

            return Function(printer)
        if kind == "query":
            target = node[1]

            def query(arg: Function) -> Function:
                if env.current_char is not None and env.current_char == target:
                    return arg(self._builtin("i", env))
                return arg(self._builtin("v", env))

            return Function(query)
        if kind == "apply":
            func = self._evaluate(node[1], env)
            arg = self._evaluate(node[2], env)
            return func(arg)
        raise RuntimeError("unknown AST node")

    # ------------------------------------------------------------------ builtins

    def _builtin(self, symbol: str, env: EvalEnv) -> Function:
        if symbol == "s":
            return Function(lambda x: Function(lambda y: Function(lambda z: x(z)(y(z)))))
        if symbol == "k":
            return Function(lambda x: Function(lambda y: x))
        if symbol == "i":
            return Function(lambda x: x)
        if symbol == "v":
            # void: applied to any argument, returns itself (a sink)
            sink: Function
            sink = Function(lambda x: sink)
            return sink
        if symbol == "r":
            # spec: r is shorthand for .<newline>
            def newline(arg: Function) -> Function:
                env.stdout.append("\n")
                return arg

            return Function(newline)
        if symbol == "@":
            def read_char(arg: Function) -> Function:
                ch = env.input_stream.read_char()
                if ch is None:
                    env.current_char = None
                    return arg(self._builtin("v", env))
                env.current_char = ch
                return arg(self._builtin("i", env))

            return Function(read_char)
        if symbol == "|":
            def reprint(arg: Function) -> Function:
                if env.current_char is None:
                    return arg(self._builtin("v", env))
                env.stdout.append(env.current_char)
                return arg(self._builtin("i", env))

            return Function(reprint)
        raise RuntimeError(f"unsupported builtin '{symbol}'")
