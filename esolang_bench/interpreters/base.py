from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

ErrorType = Literal[
    "ok",
    "compile_error",
    "runtime_error",
    "timeout_error",
    "internal_error",
]


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    error_type: ErrorType
    trace: Optional[Dict[str, Any]] = None


class BaseInterpreter:
    """Base class that enforces the benchmarking ExecutionResult contract."""

    language_name: str = "unknown"

    def run(
        self,
        code: str,
        stdin: str | bytes | None = None,
        timeout_seconds: float = 5.0,
    ) -> ExecutionResult:
        """Run the interpreter inside a short-lived worker with timeout handling."""
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=self.language_name)
        try:
            future = executor.submit(self._execute, code, stdin)
            return future.result(timeout=timeout_seconds)
        except TimeoutError:
            return ExecutionResult(
                stdout="",
                stderr=f"{self.language_name} timeout after {timeout_seconds:.2f}s",
                exit_code=1,
                error_type="timeout_error",
            )
        except Exception as exc:  # pragma: no cover - defensive path
            return ExecutionResult(
                stdout="",
                stderr=f"{self.language_name} internal error: {exc}",
                exit_code=1,
                error_type="internal_error",
            )
        finally:
            executor.shutdown(cancel_futures=True)

    def _execute(self, code: str, stdin: str | bytes | None) -> ExecutionResult:
        raise NotImplementedError
