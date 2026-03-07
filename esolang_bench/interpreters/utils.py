from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Deque, Optional
from collections import deque


class InputBuffer:
    """Shared textual input stream that supports char and integer reads."""

    def __init__(self, data: str | bytes | None):
        if data is None:
            decoded = ""
        elif isinstance(data, bytes):
            decoded = data.decode("utf-8", errors="ignore")
        else:
            decoded = data
        self._stream = io.StringIO(decoded)

    def read_char(self) -> Optional[str]:
        char = self._stream.read(1)
        return char if char != "" else None

    def read_number(self) -> Optional[int]:
        # Skip whitespace
        ch = self._stream.read(1)
        while ch != "" and ch.isspace():
            ch = self._stream.read(1)

        if ch == "":
            return None

        # Read optional sign
        sign = 1
        if ch in "+-":
            sign = -1 if ch == "-" else 1
            ch = self._stream.read(1)

        if ch == "" or (not ch.isdigit()):
            return None

        digits = [ch]
        ch = self._stream.read(1)
        while ch != "" and ch.isdigit():
            digits.append(ch)
            ch = self._stream.read(1)

        if ch != "":
            self._stream.seek(self._stream.tell() - 1)

        try:
            value = int("".join(digits))
        except ValueError:
            return None
        return sign * value


def coerce_input(data: str | bytes | None) -> InputBuffer:
    return InputBuffer(data)


def deque_from_bytes_or_str(data: str | bytes | None) -> Deque[int]:
    if data is None:
        return deque()
    if isinstance(data, bytes):
        return deque(data)
    return deque(ord(ch) for ch in data)
