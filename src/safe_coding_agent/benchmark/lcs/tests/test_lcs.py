import pytest

from solution import lcs


def _is_subsequence(x, y):
    it = iter(y)
    return all(c in it for c in x)


@pytest.mark.parametrize("a, b, length", [
    ("ABCBDAB", "BDCABA", 4), ("AGGTAB", "GXTXAYB", 4), ("", "ABC", 0), ("ABC", "DEF", 0),
])
def test_lcs(a, b, length):
    result = lcs(a, b)
    assert len(result) == length
    assert _is_subsequence(result, a) and _is_subsequence(result, b)
