from esolang_bench.interpreters import get_interpreter


def test_unlambda_outputs_text():
    program = "`.i`.H i"
    result = get_interpreter("unlambda").run(program)
    assert result.stdout == "Hi"
    assert result.error_type == "ok"


def test_unlambda_compile_error_unknown_token():
    result = get_interpreter("unlambda").run("x")
    assert result.error_type == "compile_error"


def test_unlambda_runtime_error_missing_input():
    result = get_interpreter("unlambda").run("`ri")
    assert result.error_type == "runtime_error"
