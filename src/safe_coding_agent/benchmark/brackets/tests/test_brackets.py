import pytest

from solution import is_balanced


@pytest.mark.parametrize("s, expected", [
    ("", True), ("a(b)c[d]{e}", True), ("([{}])", True),
    ("([)]", False), ("((", False), ("}", False),
])
def test_is_balanced(s, expected):
    assert is_balanced(s) is expected
