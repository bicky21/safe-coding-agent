import pytest

from solution import wrap_text


@pytest.mark.parametrize("text, width, expected", [
    ("", 5, []),
    ("   ", 5, []),
    ("the quick brown fox", 10, ["the quick", "brown fox"]),
    ("a  b\nc", 3, ["a b", "c"]),
    ("abcdefghijkl xy", 5, ["abcde", "fghij", "kl xy"]),
    ("supercalifragilistic is long", 8, ["supercal", "ifragili", "stic is", "long"]),
    ("hi abcdef", 3, ["hi", "abc", "def"]),
])
def test_wrap_text(text, width, expected):
    assert wrap_text(text, width) == expected
