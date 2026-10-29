import pytest

from solution import nth_weekday


@pytest.mark.parametrize("year, month, weekday, n, expected", [
    (2026, 10, 3, 1, 1),      # first Thursday of Oct 2026
    (2026, 10, 3, 2, 8),
    (2026, 10, 3, -1, 29),    # last Thursday
    (2026, 10, 3, 5, 29),
    (2024, 2, 3, -1, 29),     # leap year
    (2026, 2, 0, 1, 2),
    (2026, 2, 0, -1, 23),
])
def test_nth_weekday(year, month, weekday, n, expected):
    assert nth_weekday(year, month, weekday, n) == expected


@pytest.mark.parametrize("args", [(2026, 2, 0, 5), (2026, 10, 3, 0), (2026, 10, 3, -6)])
def test_missing_occurrence_raises(args):
    with pytest.raises(ValueError):
        nth_weekday(*args)
