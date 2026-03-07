from esolang_bench.interpreters import get_interpreter


def test_piet_trivial_program_halts():
    result = get_interpreter("piet").run("light_red")
    assert result.stdout == ""
    assert result.error_type == "ok"


def test_piet_compile_error_bad_color():
    result = get_interpreter("piet").run("chartreuse")
    assert result.error_type == "compile_error"


def test_piet_runtime_error_stack_underflow():
    program = "light_red light_green black"
    result = get_interpreter("piet").run(program)
    assert result.error_type == "runtime_error"
