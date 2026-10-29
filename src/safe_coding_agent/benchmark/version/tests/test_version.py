import pytest

from solution import compare_versions


@pytest.mark.parametrize("a, b, expected", [
    ("1.0", "1", 0),
    ("1.10", "1.9", 1),
    ("1.2.3", "1.2.10", -1),
    ("2", "1.99.99", 1),
    ("1.0-beta", "1.0", -1),
    ("1.0", "1.0-rc", 1),
    ("1.0-alpha", "1.0-beta", -1),
    ("1.0.0-beta", "1-beta", 0),
    ("1.1-alpha", "1.0", 1),
])
def test_compare_versions(a, b, expected):
    assert compare_versions(a, b) == expected
