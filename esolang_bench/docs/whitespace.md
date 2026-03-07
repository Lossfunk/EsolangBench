# Whitespace

## Overview

Whitespace (Edwin Brady & Chris Morris, 2002) is a stack-based language whose source code contains only space, tab, and linefeed characters. The invisible syntax makes it useful for obfuscation challenges and for testing tokenizers. Our interpreter follows the traditional IMP structure (Stack Manipulation, Arithmetic, Heap Access, Flow Control, I/O) and is powerful enough to be Turing-complete thanks to arbitrary jumps and heap access.

## Syntax & Semantics

The source is tokenised into groups:

- **Stack Manipulation (` `)**: `SS` push number, `S T S` duplicate, `S T T` swap, `S T L` discard, `S L S` copy `n`th value, `S L T` slide `n` items.
- **Arithmetic (`\t `)**: combinations of two bits (`SS`, `ST`, `SL`, `TS`, `TT`) map to add, sub, mul, div, mod.
- **Heap Access (`\t\t`)**: `S` stores (address, value), `T` retrieves.
- **Control Flow (`\n`)**: `SS` label, `ST` call, `SL` jump, `TS` jump if zero, `TT` jump if negative, `TL` return, `LLL` end.
- **I/O (`\t\n`)**: `SS` output char, `ST` output number, `TS` read char, `TT` read number.

Numbers and labels are encoded in signed binary: `Space` = `0`, `Tab` = `1`, followed by a `Linefeed`.

## Execution Model

Whitespace maintains a data stack, an unbounded heap (integer address/value), and a call stack for subroutines. Our interpreter reports stack depth and the current instruction index in `trace`. Invalid opcodes, stack underflows, heap reads of unset addresses, or divide-by-zero are surfaced as `runtime_error`.

## Examples

Hello World (push characters and print):

```
SS SSSS TL
SS SSTS TL
SS STSS TL
SS STST TL
SS STTT TL
SS SLSS TL
SS SLST TL
SS SLLS TL
SS SLLT TL
SS SLTL TL
SS SLTT TL
TS  SS
TS  SS
...
```

(Use a helper to generate pushes for clarity.)

Addition program (reads two numbers and prints their sum):

```
TLTT           Read first number
TLTT           Read second number
TS SS          Add
TLST           Output number
LLL            End
```

Loop example (count down from 5 to 1):

```
SS SSSS TL     Push 5
SS_ label      Label `_`
TLSS           Output char
TS ST          Subtract 1
SLT S          Slide 0 (noop)
TS TT          Mod (ensure integer)
TS TT          Check zero
TS  jump       Jump if zero to end
LSL label      Jump back to `_`
```

Factorial skeleton using heap storage is included in the tests for reference.

## Common Pitfalls & Debugging Tips

- **Label typos**: undefined labels trigger a compile error before execution.
- **Stack underflow**: every arithmetic op pops two values; watch your push/pop balance.
- **Heap reads**: retrieving from an address that was never stored is a runtime error.
- **Infinite loops**: throttle with `.run(..., timeout_seconds=...)`.

## Usage With This Python Package

```python
from interpreters import get_interpreter

ws = get_interpreter("whitespace")
program = "  \t \n\t \n  "  # push 0, print char
result = ws.run(program)
print(result.stdout)
```

Error example:

```json
{
  "stdout": "",
  "stderr": "Whitespace runtime error: stack underflow",
  "exit_code": 1,
  "error_type": "runtime_error",
  "trace": {
    "steps": 3,
    "ip": 2,
    "stack_depth": 0
  }
}
```
