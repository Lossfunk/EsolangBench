from esolang_bench.interpreters import get_interpreter


def test_brainfuck_hello_world():
    program = (
        "++++++++++[>+++++++>++++++++++>+++>+<<<<-]>++.>+.+++++++..+++.>++."
        "<<+++++++++++++++.>.+++.------.--------.>+.>."
    )
    result = get_interpreter("brainfuck").run(program)
    assert result.stdout == "Hello World!\n"
    assert result.error_type == "ok"


def test_brainfuck_add_two_digits():
    minus_48 = "-" * 48
    plus_48 = "+" * 48
    program = (
        "," + minus_48 + "[>+<-]"
        + ",[-]"
        + "," + minus_48 + "[>+<-]"
        + ">" + plus_48 + "."
    )
    result = get_interpreter("brainfuck").run(program, stdin="3 4")
    assert result.stdout == "7"
    assert result.error_type == "ok"


def test_brainfuck_compile_error():
    result = get_interpreter("brainfuck").run("+]")
    assert result.error_type == "compile_error"
    assert result.exit_code != 0


def test_brainfuck_runtime_error_pointer_underflow():
    result = get_interpreter("brainfuck").run("<")
    assert result.error_type == "runtime_error"
    assert "pointer" in result.stderr
