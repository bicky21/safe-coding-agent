import pytest

from solution import compress


@pytest.mark.parametrize("s, expected", [
    ("", ""),
    ("abc", "abc"),
    ("aaabcc", "3ab2c"),
    ("aabbbaa", "2a3b2a"),
    ("a" * 9, "9a"),
    ("a" * 10, "9aa"),
    ("a" * 12, "9a3a"),
    ("x" * 19 + "y", "9x9xxy"),
])
def test_compress(s, expected):
    assert compress(s) == expected
