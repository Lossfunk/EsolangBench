# Unlambda

## Overview

Unlambda (David Madore, 2000) is a combinatory logic language made entirely of functions. Its core instructions—`k`, `s`, `i`, the backtick application operator, and the output combinator `.`—provide a minimalist playground for higher-order programming. Thanks to the expressive power of the SKI calculus, Unlambda is Turing-complete despite its tiny surface syntax.

## Syntax & Semantics

Tokens are single characters; whitespace is ignored. Key constructs:

- `` `xy `` applies expression `x` to `y`. Application associates to the left: `` `abc `` means `` (`a`b)c ``.
- `k`: the K combinator (`λx.λy.x`).
- `s`: the S combinator (`λx.λy.λz. x z (y z)`).
- `i`: identity (`λx.x`).
- `r`: reads one character from stdin, emits it, and returns its argument (raises a runtime error if input is exhausted).
- `.c`: outputs the character `c` when applied to an argument (returns that argument).
- `#`: starts a comment that runs until the next newline (supported by this interpreter).

Our implementation covers the classic SKI + output core, which is sufficient for most macro demonstrations and for continuing self-hosted scaffolding experiments.

## Execution Model

The interpreter parses the source into an AST of nested applications and combinators, then evaluates it eagerly. Values are represented as callable objects (functions taking and returning other functions). Output is buffered and returned via the ExecutionResult. Runtime trace information currently reports how many characters were emitted.

## Examples

Hello World (`.` combinators applied to `i`):

```
`.H`.e`.l`.l`.o`. .`.W`.o`.r`.l`.di
```

Simple arithmetic-like combinators (Church numerals encoded in SKI) can be constructed, for example:

```
``s`k``si.k
```

Conditional (mocked through SKI):

```
``k.a`ki
```

Factorial-like programs (using recursive combinators) can be built, but are lengthy; see `tests/test_unlambda.py` for a working minimalist sample.

## Common Pitfalls & Debugging Tips

- **Missing arguments**: an application like `` `k `` without a second operand results in a compile error (“unexpected end of program”).
- **Unsupported tokens**: anything outside `k`, `s`, `i`, `` ` ``, `.`, or `#` comments is reported as a compile error.
- **Non-terminating combinators**: wrap `.run` with a low `timeout_seconds` value when experimenting with fixed-point combinators.

## Usage With This Python Package

```python
from interpreters import get_interpreter

un = get_interpreter("unlambda")
program = "`.A`.B i"
result = un.run(program)
print(result.stdout)  # 'AB'
```

Error example (unknown token):

```json
{
  "stdout": "",
  "stderr": "Unlambda compile error: unsupported token 'x'",
  "exit_code": 1,
  "error_type": "compile_error"
}
```

Timeout example:

```python
omega = "```sii"  # classic non-terminator
res = un.run(omega, timeout_seconds=0.01)
# res.error_type == "timeout_error"
```
