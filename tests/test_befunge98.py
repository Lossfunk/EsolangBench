from esolang_bench.interpreters import get_interpreter


def test_befunge_hello_world():
    program = '>\"!dlroW ,olleH\">:#,_@'
    result = get_interpreter("befunge98").run(program)
    assert result.stdout.strip() == "Hello, World!"
    assert result.error_type == "ok"


def test_befunge_compile_error_on_control_character():
    result = get_interpreter("befunge98").run("\x01")
    assert result.error_type == "compile_error"


def test_befunge_runtime_error_division_by_zero():
    program = "10/.@"
    result = get_interpreter("befunge98").run(program)
    assert result.error_type == "runtime_error"
    assert "division by zero" in result.stderr
