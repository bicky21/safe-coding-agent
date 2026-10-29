"""Reference solution for the recurring-events task (used only to check the task's tests)."""

import calendar
from datetime import date, timedelta
from itertools import combinations

from .rules import parse_rule


def _matches(rule, start, d):
    if d < start:
        return False
    if rule.freq == "daily":
        return (d - start).days % rule.interval == 0
    if rule.freq == "weekly":
        week0 = start - timedelta(days=start.weekday())
        weeks = (d - week0).days // 7
        days = rule.weekdays or (start.weekday(),)
        return weeks % rule.interval == 0 and d.weekday() in days
    if rule.freq == "monthly":
        months = (d.year - start.year) * 12 + d.month - start.month
        if months % rule.interval:
            return False
        if rule.nth:
            n, wd = rule.nth
            if d.weekday() != wd:
                return False
            last = calendar.monthrange(d.year, d.month)[1]
            if n == -1:
                return d.day + 7 > last
            return (d.day - 1) // 7 + 1 == n
        return d.day == (rule.month_day or start.day)
    # yearly
    return (d.year - start.year) % rule.interval == 0 and (d.month, d.day) == (start.month, start.day)


def occurrences(event, start, end):
    if not event.rule:
        dates = [event.start]
    else:
        rule = parse_rule(event.rule)
        last = end if rule.until is None else min(end, rule.until)
        dates, d, n = [], event.start, 0
        while d <= last:
            if _matches(rule, event.start, d):
                n += 1
                dates.append(d)
                if rule.count is not None and n >= rule.count:
                    break
            d += timedelta(days=1)
    return sorted({d for d in dates if start <= d <= end and d not in event.exceptions})


def conflicts(events, start, end):
    by_day = {}
    for e in events:
        for d in occurrences(e, start, end):
            by_day.setdefault(d, set()).add(e.title)
    out = []
    for d, titles in by_day.items():
        for a, b in combinations(sorted(titles), 2):
            out.append((d, a, b))
    return sorted(out)
