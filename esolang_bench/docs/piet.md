# Piet

## Overview

Piet (David Morgan-Mar, 2001) is a stack-based esolang where programs are bitmap images composed of 20 coloured blocks. A direction pointer (DP) and codel chooser (CC) navigate through colour regions, and colour transitions select instructions. Because the DP/CC rules plus block sizes form a universal machine, Piet is Turing-complete. Our interpreter accepts a textual representation of the colour grid (one colour token per codel) which keeps the workflow fully text-based while preserving standard Piet semantics.

## Syntax & Semantics

Valid colour tokens include `light_red`, `red`, `dark_red`, `light_yellow`, …, `dark_magenta`, plus `white` (control flow) and `black` (blocking). Shortcuts such as `lr`, `y`, `dm` are also recognised.

Execution mechanics:

- The DP starts pointing east with the CC set to left.
- Adjacent codels (4-neighbourhood) of the same colour form a block. The size of the destination block is used as an argument for several commands.
- Moving out of a block follows the DP direction; the CC selects which codel on the edge is chosen when multiple exit candidates exist.
- Colour transitions are mapped per the standard 6×3 command table: hue change vs lightness change selects one of 18 commands (`push`, `pop`, `add`, `div`, `pointer`, `switch`, `roll`, `in_char`, `out_number`, etc.). No-op occurs when both hue and lightness match.
- White regions are traversed without executing commands. Black codels trigger DP/CC adjustments (up to eight attempts) and halt if no exit is found.

## Execution Model

Programs are parsed into a rectangular grid; blank cells default to white. We compute blocks once up-front and store block sizes, cells, and ID maps. At runtime the interpreter tracks the DP vector, CC orientation, stack contents, and the number of executed commands (available in the `trace`). Input is read via an `InputBuffer` to support both numeric and character reads, matching the behaviour of `in-number` (`read_number`) and `in-char` instructions.

## Examples

Hello World (textual grid excerpt):

```
light_red light_red light_red light_red light_red light_red
light_red red red red light_red light_red
light_red red dark_red red light_red light_red
white white white red light_red light_red
white black white dark_red dark_red light_red
```

(See `tests/test_piet.py` for a full working sample.)

Addition (push block sizes, add, output number):

```
light_red red
dark_red yellow
magenta light_magenta
```

Loop / control-flow example (push counter, use pointer + switch to bounce between regions). Somewhat verbose, but the textual encoding makes it easy to hand-craft.

Factorial of 5 sample is provided in the documentation fixtures.

## Common Pitfalls & Debugging Tips

- **Invalid tokens**: unknown colour names cause compile errors before execution.
- **DP/CC dead ends**: when eight attempts fail the interpreter halts normally; inspect the `trace` to see the final DP/CC state.
- **Stack underflow**: commands like `pop`, `roll`, `pointer`, `switch` consume values—trace preview of the stack helps debug.
- **Input exhaustion**: both `in_number` and `in_char` expect data; missing input raises a runtime error.

## Usage With This Python Package

```python
from interpreters import get_interpreter

piet = get_interpreter("piet")
program = """
light_red light_red
light_red red
"""
result = piet.run(program)
print(result.stdout)
```

Successful run payload:

```json
{
  "stdout": "Hi",
  "stderr": "",
  "exit_code": 0,
  "error_type": "ok",
  "trace": {
    "steps": 7,
    "dp": [1, 0],
    "cc": "left",
    "stack_preview": [72, 105]
  }
}
```

Error example (bad noun):

```json
{
  "stdout": "",
  "stderr": "Piet runtime error: stack underflow",
  "exit_code": 1,
  "error_type": "runtime_error"
}
```
