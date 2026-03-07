# Shakespeare Programming Language (SPL)

## Overview

SPL (Karl Hasselström & Jon Åslund, 2001) dresses stack-based computation in the trappings of Elizabethan theatre. Characters speak in acts and scenes, using flowery prose to push, pop, and manipulate values. Because characters operate on unbounded stacks and can perform arbitrary jumps (scene changes), SPL is Turing-complete. Our interpreter implements the pragmatic subset most scripts rely on (assignments, arithmetic phrases, memory pushes/pops, conditional jumps, and I/O) while keeping the stage-direction flavour intact.

## Syntax & Semantics

High-level structure:

- Optional dramatis personae section (`Romeo, a test subject.`).
- Acts and scenes (`Act I:`, `Scene I: The Beginning.`). Scene names become jump labels.
- Stage directions (`Enter Romeo and Juliet.`, `Exit Romeo.`).
- Dialogue (`Romeo:` followed by sentences).

Supported sentence types inside dialogue:

| Sentence | Effect |
| -------- | ------ |
| `Remember <expr>.` | Push the evaluated expression onto the speaker’s stack. |
| `Recall your past.` | Pop the stack. |
| `You are <expr>.` | Assign the evaluated expression to the top of the stack (push if empty). |
| `Speak your mind.` | Output the top of the stack as a character. |
| `Open your heart.` | Output the top as a number. |
| `Listen to your heart.` | Read a number into the stack. |
| `Listen to your head.` | Read a character (ASCII code) into the stack. |
| `If so, let us proceed to Scene X.` | Jump if TOS > 0. |
| `If not, let us proceed to Scene X.` | Jump if TOS ≤ 0. |
| `Let us proceed to Scene X.` | Unconditional jump. |

Expressions may be:

- Literals (`123`, `-5`, `nothing`, `yourself`).
- Arithmetic phrases (`the sum of ... and ...`, `the difference between ... and ...`, `the product of ... and ...`, `the quotient between ... and ...`).
- Flowery noun phrases (e.g., `a noble hero`), where adjectives modify the magnitude and nouns provide base values. Built-in adjectives and nouns follow the standard SPL conventions (see `interpreters/shakespeare.py`).

## Execution Model

Every character owns a private stack. Only characters currently “on stage” (after an `Enter` direction) may speak. The interpreter keeps track of the stage cast, evaluates expressions on demand, and enforces scene jumps through a dictionary of scene names → indices. The runtime trace exposes the number of executed dialogue statements, the last speaker, and the set of characters currently on stage.

## Examples

Hello World (excerpt):

```
Romeo, a test subject.
Juliet, another.

Act I: Testing
Scene I: Greetings
Enter Romeo and Juliet.
Romeo:
Remember a noble hero.
Speak your mind.
Remember a quick hero.
Speak your mind.
Exit Romeo and Juliet.
```

Addition (reads two numbers and announces the sum):

```
Scene I: Math
Enter Romeo.
Romeo:
Listen to your heart.
Listen to your heart.
Remember yourself.
Remember the sum of yourself and yourself.
Open your heart.
Exeunt.
```

Control flow (loop until zero):

```
Scene I: Start
Enter Romeo.
Romeo:
You are 5.
Scene II: Loop
Romeo:
Speak your mind.
You are the difference between yourself and a brave hero.
If so, let us proceed to Scene II.
```

Factorial and other arithmetic-heavy scripts can be assembled using the noun/adjective arithmetic plus conditional jumps.

## Common Pitfalls & Debugging Tips

- **Speaker not on stage**: you must `Enter` characters before they speak; otherwise the interpreter raises a runtime error naming the offender.
- **Unknown scenes**: scene names are case-insensitive but must exist; typos show up as runtime errors when a jump fires.
- **Expression vocabulary**: using adjectives or nouns outside the built-in tables results in runtime errors (“unknown noun”).
- **Divide by zero**: `the quotient between ...` checks for zero and raises a runtime error.

## Usage With This Python Package

```python
from interpreters import get_interpreter

spl = get_interpreter("shakespeare")
script = """
Romeo, a hero.
Act I: Numbers
Scene I: Start
Enter Romeo.
Romeo:
Remember 72.
Speak your mind.
Exit Romeo.
"""
result = spl.run(script)
print(result.stdout)  # 'H'
```

Success payload:

```json
{
  "stdout": "Hi",
  "stderr": "",
  "exit_code": 0,
  "error_type": "ok",
  "trace": {
    "steps": 4,
    "last_speaker": "Romeo",
    "stage": []
  }
}
```

Compile error example (unknown sentence):

```json
{
  "stdout": "",
  "stderr": "SPL compile error: Unsupported sentence: 'Begone!'",
  "exit_code": 1,
  "error_type": "compile_error"
}
```
