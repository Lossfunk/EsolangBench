from esolang_bench.interpreters import get_interpreter


SCRIPT_OK = """
Romeo, a hero.
Juliet, a heroine.

Act I: Start
Scene I: Opening
Enter Romeo.
Romeo:
Remember 72.
Speak your mind.
Exit Romeo.
"""


def test_shakespeare_basic_output():
    result = get_interpreter("shakespeare").run(SCRIPT_OK)
    assert result.stdout == "H"
    assert result.error_type == "ok"


def test_shakespeare_compile_error_unknown_sentence():
    script = """
Romeo, a hero.
Act I: Broken
Scene I: Chaos
Enter Romeo.
Romeo:
Begone.
"""
    result = get_interpreter("shakespeare").run(script)
    assert result.error_type == "compile_error"


def test_shakespeare_runtime_error_offstage_speaker():
    script = """
Romeo, a hero.
Act I: Start
Scene I: Trouble
Romeo:
Remember 1.
"""
    result = get_interpreter("shakespeare").run(script)
    assert result.error_type == "runtime_error"
