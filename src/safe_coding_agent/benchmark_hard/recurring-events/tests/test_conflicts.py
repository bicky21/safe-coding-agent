from datetime import date

from cal.models import Event
from cal.schedule import conflicts


def test_conflicts_pairs_sorted():
    events = [
        Event("Standup", date(2026, 10, 1), "weekly on fri"),
        Event("Gym", date(2026, 10, 1), "daily for 5 times", {date(2026, 10, 3)}),
        Event("Alpha", date(2026, 10, 2)),
    ]
    assert conflicts(events, date(2026, 10, 1), date(2026, 10, 5)) == [
        (date(2026, 10, 2), "Alpha", "Gym"),
        (date(2026, 10, 2), "Alpha", "Standup"),
        (date(2026, 10, 2), "Gym", "Standup"),
    ]


def test_no_conflicts_outside_the_window_or_on_exceptions():
    events = [
        Event("A", date(2026, 10, 1), "daily"),
        Event("B", date(2026, 10, 3), None),
        Event("C", date(2026, 10, 4), "daily", {date(2026, 10, 4)}),
    ]
    assert conflicts(events, date(2026, 10, 1), date(2026, 10, 2)) == []
    assert conflicts(events, date(2026, 10, 3), date(2026, 10, 5)) == [
        (date(2026, 10, 3), "A", "B"),
        (date(2026, 10, 5), "A", "C"),
    ]
