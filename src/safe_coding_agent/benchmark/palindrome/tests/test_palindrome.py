import pytest

from solution import is_palindrome


@pytest.mark.parametrize("s, expected", [
    ("A man, a plan, a canal: Panama", True),
    ("racecar", True),
    ("hello", False),
    ("", True),
])
def test_is_palindrome(s, expected):
    assert is_palindrome(s) is expected
