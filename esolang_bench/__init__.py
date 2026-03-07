"""EsoLang-Bench: Evaluating LLMs on esoteric programming language generation."""

__version__ = "0.1.0"

from esolang_bench.interpreters import get_interpreter, BaseInterpreter, ExecutionResult

__all__ = ["get_interpreter", "BaseInterpreter", "ExecutionResult", "__version__"]
