from esolang_bench.interpreters import get_interpreter


def test_unlambda_outputs_text():
    program = "`.i`.H i"
    result = get_interpreter("unlambda").run(program)
    assert result.stdout == "Hi"
    assert result.error_type == "ok"


def test_unlambda_r_prints_newline():
    """`r` is the spec-defined shorthand for .<newline>; it prints '\\n', not 'r'."""
    result = get_interpreter("unlambda").run("`ri")
    assert result.stdout == "\n"
    assert result.error_type == "ok"


def test_unlambda_dot_n_prints_literal_n():
    """`.n` prints the literal character 'n', not a newline."""
    result = get_interpreter("unlambda").run("`.ni")
    assert result.stdout == "n"
    assert result.error_type == "ok"


def test_unlambda_input_read_via_at_and_pipe():
    """`@` reads a character into the current-char register and calls its
    argument with identity on success or void on EOF. `|` re-emits the
    current character. The standard echo idiom is ``@|i.
    """
    result = get_interpreter("unlambda").run("``@|i", stdin="X")
    assert result.stdout == "X"
    assert result.error_type == "ok"


def test_unlambda_query_matches_current_char():
    """`?x` returns identity when the current character matches the literal x,
    void otherwise. Reading 'A' then `?A` should match.
    """
    # ``@`?Aii: read input, test if it's 'A'; the test should not error out.
    result = get_interpreter("unlambda").run("``@`?Aii", stdin="A")
    assert result.error_type == "ok"


def test_unlambda_compile_error_unknown_token():
    result = get_interpreter("unlambda").run("x")
    assert result.error_type == "compile_error"
