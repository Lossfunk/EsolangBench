from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass
class BenchmarkMetrics:
    regime: str
    total: int = 0
    solved: int = 0
    solved_attempts: list[int] = field(default_factory=list)
    failure_errors: Counter = field(default_factory=Counter)

    def record_result(self, solved: bool, attempts: int, failure_error_types: list[str] | None = None) -> None:
        self.total += 1
        if solved:
            self.solved += 1
            self.solved_attempts.append(attempts)
        elif failure_error_types:
            self.failure_errors.update(failure_error_types)

    def accuracy(self) -> float:
        return self.solved / self.total if self.total else 0.0

    def average_attempts(self) -> float:
        if not self.solved_attempts:
            return 0.0
        return sum(self.solved_attempts) / len(self.solved_attempts)

    def summary(self) -> str:
        lines = [
            f"Regime: {self.regime}",
            f"Problems attempted: {self.total}",
            f"Problems solved: {self.solved}",
            f"Accuracy: {self.accuracy():.2%}",
        ]
        if self.regime in ("self_scaffolding", "textual_self_scaffolding", "react"):
            lines.append(f"Average attempts (solved): {self.average_attempts():.2f}")
            if self.failure_errors:
                lines.append(f"Failure error types: {dict(self.failure_errors)}")
        return "\n".join(lines)
