import pytest

from solution import parse_duration


@pytest.mark.parametrize("s, expected", [
    ("1h30m", 5400), ("2d", 172800), ("1D 2H 3M 4S", 93784), ("45s", 45), ("0m", 0),
])
def test_valid(s, expected):
    assert parse_duration(s) == expected


@pytest.mark.parametrize("bad", ["", "10", "h", "1x", "1m1h", "1h1h", "1h 30"])
def test_invalid_raises(bad):
    with pytest.raises(ValueError):
        parse_duration(bad)
