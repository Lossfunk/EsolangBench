# Thue Language

Thue is a string-rewriting esoteric language. Programs consist of rewrite rules and an optional initial string. The runtime repeatedly applies rules to rewrite the working string until no rule matches. When a rule rewrites to the special symbol `::=` and a string, the string is appended to stdout.

## Syntax

A Thue program has rules like `pattern ::= replacement` terminated by a blank line, followed by the initial string. A special replacement `~` reads one character from stdin and substitutes it into the string.

Example (Hello World):
```
`#`::=Hello World!
::=~
#
```

To run Thue code, we repeatedly find the first matching pattern and replace it with the rule's replacement. If no rules match, the program halts.

Our interpreter execution is deterministic:
- We scan rules in order; the first matching rule is applied.
- Output is produced via explicit `::=` print rules.

