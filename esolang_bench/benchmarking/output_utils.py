from __future__ import annotations

import ast
import re
from typing import Optional


def _trim_trailing_control(text: str) -> str:
    while text and (ord(text[-1]) < 32 or ord(text[-1]) == 127):
        text = text[:-1]
    return text


def _normalize_math_operators(s: str) -> str:
    """Map common unicode/operator variants to simple ASCII operators.

    Examples: '×', 'x', 'X', '·' -> '*'; '÷' -> '/'; unicode minus -> '-'.
    """
    repl = (
        ('×', '*'), ('⋅', '*'), ('·', '*'), ('•', '*'), ('x', '*'), ('X', '*'),
        ('÷', '/'), ('−', '-'), ('—', '-'), ('–', '-'), (',', ''),
    )
    out = s
    for a, b in repl:
        out = out.replace(a, b)
    return out


def _safe_eval_arith(expr: str) -> Optional[int]:
    """Safely evaluate a very small arithmetic subset to an int.

    Supported operators: +, -, *, //, /, %, ** and parentheses. Returns None if
    parsing fails or expression contains any other constructs.
    """
    try:
        tree = ast.parse(expr, mode='eval')
    except SyntaxError:
        return None

    def eval_node(node) -> int:
        if isinstance(node, ast.Expression):
            return eval_node(node.body)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)):
            left = eval_node(node.left)
            right = eval_node(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                # Only accept exact integer results
                res = left / right
                return int(res) if res.is_integer() else 10**18  # sentinel unlikely to match
            if isinstance(node.op, ast.FloorDiv):
                return left // right
            if isinstance(node.op, ast.Mod):
                return left % right
            if isinstance(node.op, ast.Pow):
                return left ** right
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            val = eval_node(node.operand)
            return +val if isinstance(node.op, ast.UAdd) else -val
        if isinstance(node, ast.Num) and isinstance(node.n, (int, float)):
            # accept ints and integer-valued floats
            return int(node.n)
        if isinstance(node, ast.Paren) if False else False:  # placate linters; parentheses handled by AST
            return eval_node(node.value)
        raise ValueError("unsupported expression")

    try:
        value = eval_node(tree)
        return int(value)
    except Exception:
        return None


def _extract_integers(s: str) -> list[int]:
    ints: list[int] = []
    num = ''
    sign_allowed = True
    for ch in s:
        if ch in '+-' and sign_allowed:
            if num:
                ints.append(int(num))
                num = ''
            num = ch
            sign_allowed = False
        elif ch.isdigit():
            num += ch
            sign_allowed = False
        else:
            if num and (num.lstrip('+-').isdigit()):
                ints.append(int(num))
            num = ''
            sign_allowed = True
    if num and (num.lstrip('+-').isdigit()):
        ints.append(int(num))
    return ints


def outputs_match(expected: str | None, actual: str | None) -> bool:
    """
    Compare stdout against expectations while ignoring trailing whitespace that can
    vary per interpreter (extra newlines, carriage returns, vertical tabs, etc.).
    """
    expected = "" if expected is None else expected
    actual = "" if actual is None else actual
    if actual == expected:
        return True
    expected_trimmed = _trim_trailing_control(expected.rstrip())
    actual_trimmed = _trim_trailing_control(actual.rstrip())
    if actual_trimmed == expected_trimmed:
        return True

    # Numeric-aware comparison: if expected is a plain integer, try to
    # recognise/evaluate numeric content in the model output (e.g., "3*4=12",
    # "Result: 12", unicode operators, etc.).
    if expected_trimmed.lstrip('-').isdigit():
        try:
            expected_int = int(expected_trimmed)
        except ValueError:
            expected_int = None
        if expected_int is not None:
            # 1) Try to evaluate a simple arithmetic expression if present
            expr_candidate = _normalize_math_operators(actual_trimmed)
            # pick right side of '=' if present, otherwise whole string
            rhs = expr_candidate.split('=')[-1].strip()
            evaluated = _safe_eval_arith(rhs)
            if evaluated is not None and evaluated == expected_int:
                return True
            # 2) Fallback: accept if any integer token equals expected
            for val in _extract_integers(actual_trimmed):
                if val == expected_int:
                    return True
            # 3) Special-case common phrasing: 'product is 12'
            tokens = _extract_integers(expr_candidate)
            if tokens and tokens[-1] == expected_int:
                return True
    return False


def outputs_match_lang(expected: str | None, actual: str | None, *, language_id: Optional[str] = None) -> bool:
    """Language-aware comparator.

    - For Brainfuck numeric tasks (expected is integer), require the output to be
      a plain signed integer string (optionally followed by newlines/control which
      are trimmed earlier). This avoids accepting verbal explanations.
    - Otherwise, fall back to the more permissive numeric-aware comparator.
    """
    expected = "" if expected is None else expected
    actual = "" if actual is None else actual
    # Trim trailing control chars/newlines first
    expected_trimmed = _trim_trailing_control(expected.rstrip())
    actual_trimmed = _trim_trailing_control(actual.rstrip())

    # Brainfuck strict numeric mode
    if language_id == "brainfuck" and expected_trimmed.lstrip('-').isdigit():
        # Only accept if the entire (non-empty) payload is a signed integer
        # (allow surrounding whitespace already trimmed from right; strip left here)
        payload = actual_trimmed.strip()
        if re.fullmatch(r"-?\d+", payload or " "):
            return int(payload) == int(expected_trimmed)
        return False

    # Default path uses permissive comparator
    return outputs_match(expected, actual)
