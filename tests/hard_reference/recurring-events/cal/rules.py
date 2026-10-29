"""Reference solution for the recurring-events task (used only to check the task's tests)."""

import re
from dataclasses import dataclass
from datetime import date

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
FULL = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
NTH = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "last": -1}


def _day(name):
    name = name.strip().lower()
    if name in DAYS:
        return DAYS.index(name)
    if name in FULL:
        return FULL.index(name)
    raise ValueError(f"bad weekday {name!r}")


@dataclass
class Rule:
    freq: str                 # daily | weekly | monthly | yearly
    interval: int = 1
    weekdays: tuple = ()      # weekly
    month_day: int | None = None          # monthly on day D
    nth: tuple | None = None              # monthly on the Nth weekday: (n, weekday)
    until: date | None = None
    count: int | None = None


UNIT = {"day": "daily", "week": "weekly", "month": "monthly", "year": "yearly"}


def parse_rule(text):
    t = " ".join(text.lower().split())
    until = count = None
    m = re.search(r" until (\d{4})-(\d{2})-(\d{2})$", t)
    if m:
        until = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        t = t[:m.start()]
    else:
        m = re.search(r" for (\d+) times$", t)
        if m:
            count = int(m.group(1))
            if count < 1:
                raise ValueError("count must be >= 1")
            t = t[:m.start()]
    m = re.fullmatch(r"(daily|weekly|monthly|yearly)(?: (.*))?", t)
    if m:
        freq, interval, rest = m.group(1), 1, m.group(2)
    else:
        m = re.fullmatch(r"every (\d+) (day|week|month|year)s?(?: (.*))?", t)
        if not m:
            raise ValueError(f"cannot parse rule {text!r}")
        freq, interval, rest = UNIT[m.group(2)], int(m.group(1)), m.group(3)
        if interval < 1:
            raise ValueError("interval must be >= 1")
    rule = Rule(freq, interval, until=until, count=count)
    if rest is None:
        return rule
    if freq == "weekly":
        m = re.fullmatch(r"on ([a-z]+(?:\s*,\s*[a-z]+)*)", rest)
        if not m:
            raise ValueError(f"cannot parse rule {text!r}")
        rule.weekdays = tuple(sorted({_day(d) for d in m.group(1).split(",")}))
        return rule
    if freq == "monthly":
        m = re.fullmatch(r"on day (\d+)", rest)
        if m:
            d = int(m.group(1))
            if not 1 <= d <= 31:
                raise ValueError("day must be 1..31")
            rule.month_day = d
            return rule
        m = re.fullmatch(r"on the (1st|2nd|3rd|4th|last) ([a-z]+)", rest)
        if m:
            rule.nth = (NTH[m.group(1)], _day(m.group(2)))
            return rule
    raise ValueError(f"cannot parse rule {text!r}")
