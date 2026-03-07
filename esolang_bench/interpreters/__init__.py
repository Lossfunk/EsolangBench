from .base import BaseInterpreter, ExecutionResult
from .brainfuck import BrainfuckInterpreter
from .whitespace import WhitespaceInterpreter
from .befunge98 import Befunge98Interpreter
from .piet import PietInterpreter
from .unlambda import UnlambdaInterpreter
from .shakespeare import ShakespeareInterpreter
from .thue import ThueInterpreter

_REGISTRY = {
    "brainfuck": BrainfuckInterpreter,
    "whitespace": WhitespaceInterpreter,
    "befunge98": Befunge98Interpreter,
    "piet": PietInterpreter,
    "unlambda": UnlambdaInterpreter,
    "shakespeare": ShakespeareInterpreter,
    "thue": ThueInterpreter,
}


def get_interpreter(name: str) -> BaseInterpreter:
    key = name.lower()
    if key not in _REGISTRY:
        raise ValueError(f"Unknown esolang: {name}")
    return _REGISTRY[key]()


__all__ = [
    "BaseInterpreter",
    "ExecutionResult",
    "BrainfuckInterpreter",
    "WhitespaceInterpreter",
    "Befunge98Interpreter",
    "PietInterpreter",
    "UnlambdaInterpreter",
    "ShakespeareInterpreter",
    "get_interpreter",
]


def cli_main() -> None:
    """Entry point for ``esolang-interpret`` console script."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="esolang-interpret",
        description="Run an esoteric language interpreter on code from a file or stdin.",
    )
    parser.add_argument(
        "--language", "-l", required=True, choices=sorted(_REGISTRY), help="Esoteric language name"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--code", "-c", help="Inline source code string")
    source.add_argument("--file", "-f", help="Path to source code file")
    parser.add_argument("--input", "-i", default="", help="Stdin input for the program")
    parser.add_argument("--timeout", "-t", type=float, default=5.0, help="Timeout in seconds")
    args = parser.parse_args()

    if args.code is not None:
        code = args.code
    else:
        with open(args.file, "r", encoding="utf-8") as fh:
            code = fh.read()

    interpreter = get_interpreter(args.language)
    result = interpreter.run(code, stdin=args.input, timeout_seconds=args.timeout)
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    sys.exit(result.exit_code)
