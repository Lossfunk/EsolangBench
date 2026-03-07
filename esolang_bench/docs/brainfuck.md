# Brainfuck

## Overview

Brainfuck (Urban Müller, 1993) uses just eight single-character instructions operating on an infinite tape of bytes. Despite the tiny syntax it is Turing-complete because an unbounded tape plus conditional jumps (`[` and `]`) can simulate a simple register machine. The language is ideal for stress-testing interpreters because mistakes show up quickly as pointer underflows or unmatched brackets.

## Syntax & Semantics

| Instruction | Meaning |
| ----------- | ------- |
| `>` / `<` | Move the tape pointer right / left (our interpreter dynamically extends the tape on demand). |
| `+` / `-` | Increment / decrement the current cell (modulo 256). |
| `.` / `,` | Output / input a single byte. Input exhaustion yields `0`. |
| `[` / `]` | Jump forward / backward past the matching bracket when the current cell is zero / non-zero. |

All other characters are ignored, so comments can be written freely. Brackets must be perfectly balanced; the compiler rejects mismatches with `error_type="compile_error"`.

## Execution Model

Execution starts with a zero-filled tape and pointer at cell `0`. The interpreter tracks the number of steps, current pointer position, and a preview of the tape to expose in diagnostics. Jump targets are resolved once before execution so bracket mismatches are caught early. Moving the pointer below zero is a runtime error; moving beyond the current tape expands it automatically.

## Examples

Hello World:

```
+++++++++[>+++++++>++++++++++>+++>+<<<<-]>++.>+.+++++++..+++.>++.<<+++++++++++++++.>.+++.------.--------.>+.>.
```

Add two ASCII digits provided on stdin and echo the sum as a digit:

```
,>,<[>+>+<<-]>>[<<+>>-]<<<++++[>++++++++<-]>.[-]
```

Loop-based control flow (prints numbers 1–5):

```
++++[>+>+<<-]>>[-<<+>>]<
[>.[-]<-]
```

Factorial of 5 (outputs 120 as a byte):

```
++++>+++++<[>[>+>+<<-]>>[-<<+>>]<<<-]>>>.[-]
```

## Common Pitfalls & Debugging Tips

- **Unmatched brackets**: compile error pinpointed via the bracket index in `stderr`.
- **Pointer underflow**: moving left from cell 0 raises a runtime error with a trace showing recent instructions.
- **Infinite loops**: use a smaller `timeout_seconds` when calling `.run` to deliberately trigger a `timeout_error`.
- **Input exhaustion**: `,` returns zero when stdin runs dry; if your program expects more input the trace helps confirm what was consumed.

## Usage With This Python Package

```python
from interpreters import get_interpreter

bf = get_interpreter("brainfuck")
result = bf.run("+++.>++.")
print(result.stdout)     # '\x03\x02'
print(result.error_type) # 'ok'
```

Example error payload:

```json
{
  "stdout": "",
  "stderr": "Brainfuck compile error: unmatched ']' at position 12",
  "exit_code": 1,
  "error_type": "compile_error",
  "trace": null
}
```

Timeout example:

```python
loop = "[-]"  # waits for cell to hit zero
res = bf.run(loop, timeout_seconds=0.01)
# res.error_type == "timeout_error"
```
