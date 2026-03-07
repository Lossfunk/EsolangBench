# Befunge-98

## Overview

Befunge (Chris Pressey, 1993) executes programs on a 2D toroidal grid with a movable instruction pointer (IP). The 1998 revision (Funge-98) adds self-modifying `p/g`, richer I/O, and concurrency hooks. Its spatial control flow and stack semantics make it a favourite stress-test for interpreters—if you can handle Befunge’s wraparound jumps, you can likely handle anything.

## Syntax & Semantics

Each cell on the playfield holds one byte, typically written as ASCII characters in the source file. Notable instructions:

- **Flow**: `> < ^ v` set direction; `?` random direction; `_` horizontal branch by top-of-stack (TOS); `|` vertical branch; `#` trampoline skip.
- **Stack ops**: digits `0-9` push literal values; `:` duplicate TOS; `\` swap TOS and NOS; `$` drop; `"` toggles string mode (push ASCII codes until the next `"`).
- **Arithmetic**: `+ - * / % ! \`` (logical not and greater-than).
- **Storage**: `p` puts a value back into the playfield; `g` fetches.
- **I/O**: `.` output number, `,` output char, `&` input number, `~` input char.
- **Misc**: `'` literal character, `k` skip N instructions, `@` halt.

Whitespace cells are no-ops. Our interpreter enforces stack underflow checks and finite instruction budgets.

## Execution Model

The playfield is rectangular (height = number of source lines, width = longest line). The IP starts at `(0,0)` heading east. After each instruction the IP moves one cell along the current direction, wrapping around the edges. String mode pushes raw bytes instead of executing instructions. Runtime trace data includes the IP coordinates, direction vector, stack depth, and the last few opcodes executed.

## Examples

Hello World:

```
>              v
v  ,olleH<     <
>48*,          @
```

Simple addition (reads two numbers, prints sum):

```
&:&+.
@
```

Loop counting down from 5 to 1:

```
08>:1-:v v *_$.@
  ^    _@
```

Prime testing (trial division) and other classic samples fit easily in the same grid.

## Common Pitfalls & Debugging Tips

- **Stack underflow**: use `:` before arithmetic when needed; the error message will name the offending instruction.
- **Division by zero**: Befunge defines it as undefined—our runtime reports a descriptive error.
- **Random branches (`?`)**: reproducibility matters for benchmarking; consider seeding your program to avoid nondeterminism.
- **Self-modification**: writing outside the original playfield wraps modulo the field dimensions; check the trace for the `p` coordinates.

## Usage With This Python Package

```python
from interpreters import get_interpreter

bef = get_interpreter("befunge98")
program = ">987v>.v\nv456<  :\n>321 ^ _@"
result = bef.run(program)
print(result.stdout)
```

Example runtime error payload:

```json
{
  "stdout": "",
  "stderr": "Befunge runtime error: stack underflow",
  "exit_code": 1,
  "error_type": "runtime_error",
  "trace": {
    "ip": {"x": 4, "y": 0, "direction": {"dx": 1, "dy": 0}},
    "stack_depth": 0,
    "last_ops": ["3,0:+", "4,0:-"]
  }
}
```
