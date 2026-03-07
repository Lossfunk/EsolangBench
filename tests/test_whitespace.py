from esolang_bench.interpreters import get_interpreter

SPACE = " "
TAB = "\t"
LF = "\n"


def push_number(value: int) -> str:
    bits = bin(abs(value))[2:] if value != 0 else ""
    encoded = "".join(SPACE if bit == "0" else TAB for bit in bits)
    sign = SPACE if value >= 0 else TAB
    return f"{SPACE}{SPACE}{sign}{encoded}{LF}"


PRINT_CHAR = f"{TAB}{LF}{SPACE}{SPACE}"
PRINT_NUMBER = f"{TAB}{LF}{SPACE}{TAB}"
READ_NUMBER = f"{TAB}{LF}{TAB}{TAB}"
RETRIEVE = f"{TAB}{TAB}{TAB}"
END = "\n\n\n"
DISCARD = f"{SPACE}{TAB}{LF}"


def test_whitespace_prints_characters():
    program = "".join(
        [
            push_number(ord("H")),
            PRINT_CHAR,
            push_number(ord("i")),
            PRINT_CHAR,
            END,
        ]
    )
    result = get_interpreter("whitespace").run(program)
    assert result.stdout == "Hi"
    assert result.error_type == "ok"


def test_whitespace_compile_error_unknown_label():
    jump = f"\n \n {SPACE}{LF}"
    result = get_interpreter("whitespace").run(jump)
    assert result.error_type == "compile_error"


def test_whitespace_runtime_error_stack_underflow():
    program = DISCARD + END
    result = get_interpreter("whitespace").run(program)
    assert result.error_type == "runtime_error"


def test_whitespace_reads_and_echoes_number():
    program = "".join(
        [
            push_number(0),
            READ_NUMBER,
            push_number(0),
            RETRIEVE,
            PRINT_NUMBER,
            END,
        ]
    )
    result = get_interpreter("whitespace").run(program, stdin="123")
    assert result.stdout == "123"
    assert result.error_type == "ok"
