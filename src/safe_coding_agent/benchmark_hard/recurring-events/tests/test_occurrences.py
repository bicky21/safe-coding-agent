from datetime import date

import pytest

from cal.models import Event
from cal.rules import parse_rule
from cal.schedule import occurrences

OCT1 = date(2026, 10, 1)          # a Thursday


def days(month, *ds, year=2026):
    return [date(year, month, d) for d in ds]


def occ(rule, start=OCT1, frm=None, to=None, exceptions=()):
    e = Event("e", start, rule, set(exceptions))
    return occurrences(e, frm or start, to or date(2026, 10, 31))


def test_single_event():
    assert occurrences(Event("x", OCT1), date(2026, 9, 1), date(2026, 12, 31)) == [OCT1]
    assert occurrences(Event("x", OCT1), date(2026, 10, 2), date(2026, 12, 31)) == []


def test_daily_until():
    assert occ("daily until 2026-10-05") == days(10, 1, 2, 3, 4, 5)


def test_every_n_days_for_n_times():
    assert occ("every 3 days for 4 times") == days(10, 1, 4, 7, 10)


def test_exceptions_still_count_toward_times():
    assert occ("daily for 5 times", exceptions=days(10, 2, 4)) == days(10, 1, 3, 5)


def test_weekly_uses_start_weekday():
    assert occ("weekly") == days(10, 1, 8, 15, 22, 29)


def test_weekly_on_days_skips_a_non_matching_start():
    assert occ("weekly on mon,wed", to=date(2026, 10, 14)) == days(10, 5, 7, 12, 14)


def test_every_two_weeks_counts_monday_based_weeks():
    # week 0 is Mon 28 Sep .. Sun 4 Oct (it contains the start, Thu 1 Oct)
    assert occ("every 2 weeks on mon,fri") == days(10, 2, 12, 16, 26, 30)


def test_monthly_day_31_skips_short_months():
    got = occ("monthly on day 31", start=date(2026, 1, 31), to=date(2026, 12, 31))
    assert got == [date(2026, m, 31) for m in (1, 3, 5, 7, 8, 10, 12)]


def test_every_two_months_for_three_times():
    got = occ("every 2 months for 3 times", start=date(2026, 1, 15), to=date(2027, 12, 31))
    assert got == [date(2026, 1, 15), date(2026, 3, 15), date(2026, 5, 15)]


def test_monthly_last_weekday():
    got = occ("monthly on the last fri", to=date(2026, 12, 31))
    assert got == [date(2026, 10, 30), date(2026, 11, 27), date(2026, 12, 25)]


def test_monthly_nth_weekday():
    got = occ("monthly on the 2nd tue", to=date(2026, 11, 30))
    assert got == [date(2026, 10, 13), date(2026, 11, 10)]


def test_yearly_on_leap_day():
    got = occ("yearly", start=date(2024, 2, 29), to=date(2032, 12, 31))
    assert got == [date(2024, 2, 29), date(2028, 2, 29), date(2032, 2, 29)]


def test_every_two_years():
    got = occ("every 2 years for 3 times", start=date(2026, 3, 10), to=date(2040, 1, 1))
    assert got == [date(2026, 3, 10), date(2028, 3, 10), date(2030, 3, 10)]


def test_query_window_inside_and_before_start():
    assert occ("daily", frm=date(2026, 10, 10), to=date(2026, 10, 12)) == days(10, 10, 11, 12)
    e = Event("e", date(2026, 10, 10), "daily")
    assert occurrences(e, date(2026, 10, 1), date(2026, 10, 12)) == days(10, 10, 11, 12)


@pytest.mark.parametrize("rule", ["Every  2   WEEKS on  Mon , fri", "every 2 weeks on monday,friday"])
def test_rules_are_case_and_space_insensitive(rule):
    assert occ(rule) == days(10, 2, 12, 16, 26, 30)


@pytest.mark.parametrize("bad", ["fortnightly", "every 0 days", "monthly on day 32", "weekly on funday",
                                 "daily until 2026-13-01", "every 2 weeks on", "daily for 0 times"])
def test_invalid_rules(bad):
    with pytest.raises(ValueError):
        parse_rule(bad)
