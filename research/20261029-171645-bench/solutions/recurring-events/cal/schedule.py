from __future__ import annotations

from datetime import date, timedelta
from itertools import combinations
from typing import List, Tuple, Set

from .models import Event
from .rules import parse_rule

def _add_months(orig: date, months: int) -> date:
    """Add months preserving day when possible, otherwise overflow to next month (will be handled)."""
    year = orig.year + (orig.month - 1 + months) // 12
    month = (orig.month - 1 + months) % 12 + 1
    day = orig.day
    # try to construct; if invalid (e.g., Feb 30) raise ValueError
    try:
        return date(year, month, day)
    except ValueError:
        # overflow: return a date that will be filtered out later
        return date(year, month, 1)  # placeholder
        

def _nth_weekday_of_month(year: int, month: int, weekday: int, ordinal: int) -> date | None:
    """Return the date of the nth weekday in a month. ordinal -1 means last."""
    # first day of month
    first = date(year, month, 1)
    # offset to first desired weekday
    offset = (weekday - first.weekday() + 7) % 7
    if ordinal > 0:
        day = 1 + offset + (ordinal - 1) * 7
        try:
            return date(year, month, day)
        except ValueError:
            return None
    else:  # last
        # find last weekday of month
        # start from first of next month then go back
        if month == 12:
            nxt = date(year + 1, 1, 1)
        else:
            nxt = date(year, month + 1, 1)
        last_day = nxt - timedelta(days=1)
        offset_back = (last_day.weekday() - weekday + 7) % 7
        day = last_day.day - offset_back
        return date(year, month, day)

def occurrences(event: Event, start: date, end: date) -> List[date]:
    """Return list of occurrence dates for the given event within [start, end]."""
    if start > end:
        return []

    # rule parsing
    rule_dict = None
    if event.rule:
        rule_dict = parse_rule(event.rule)

    results: Set[date] = set()

    # Helper to check stop conditions
    def stop_condition(current: date, occ_count: int) -> bool:
        if rule_dict:
            if rule_dict.get("until") and current > rule_dict["until"]:
                return True
            if rule_dict.get("count") is not None and occ_count >= rule_dict["count"]:
                return True
        return False

    # No rule: single occurrence on start date
    if not rule_dict:
        if event.start >= start and event.start <= end and event.start not in event.exceptions:
            results.add(event.start)
        return sorted(results)

    freq = rule_dict["freq"]
    interval = rule_dict.get("interval", 1)

    # start generating from event.start (or later)
    cur = event.start
    occ_index = 0  # number of occurrences generated (including those excluded by exceptions)

    while True:
        # stop if beyond end or rule limits
        if cur > end:
            break
        if stop_condition(cur, occ_index):
            break

        # Determine if cur matches rule specifics
        match = False
        if freq == "daily":
            match = True
        elif freq == "weekly":
            weekdays = rule_dict.get("weekdays")
            if weekdays is None:
                # default: weekday of event.start
                weekdays = [event.start.weekday()]
            # compute week number relative to event.start week
            # week 0 is Monday-Sunday containing event.start
            week_start = event.start - timedelta(days=event.start.weekday())
            weeks_since = (cur - week_start).days // 7
            if weeks_since % interval == 0 and cur.weekday() in weekdays:
                match = True
        elif freq == "monthly":
            # compute month offset from start month
            month_offset = (cur.year - event.start.year) * 12 + (cur.month - event.start.month)
            if month_offset % interval != 0:
                match = False
            else:
                typ = rule_dict.get("type")
                if typ is None or typ == "day_of_month":
                    day = rule_dict.get("day", event.start.day)
                    if cur.day == day:
                        match = True
                elif typ == "nth_weekday":
                    ord_ = rule_dict["ordinal"]
                    wkday = rule_dict["weekday"]
                    cand = _nth_weekday_of_month(cur.year, cur.month, wkday, ord_)
                    if cand == cur:
                        match = True
        elif freq == "yearly":
            year_offset = cur.year - event.start.year
            if year_offset % interval != 0:
                match = False
            else:
                if cur.month == event.start.month and cur.day == event.start.day:
                    match = True

        if match:
            occ_index += 1
            if cur >= start and cur <= end and cur not in event.exceptions:
                results.add(cur)

        # advance to next candidate date
        if freq == "daily":
            cur = cur + timedelta(days=interval)
        elif freq == "weekly":
            # move to next day; we will rely on loop to skip non‑matching weeks
            cur = cur + timedelta(days=1)
        elif freq == "monthly":
            # move to next day; month handling via loop
            cur = cur + timedelta(days=1)
        elif freq == "yearly":
            cur = cur + timedelta(days=1)
        else:
            break

    return sorted(results)


def conflicts(events: List[Event], start: date, end: date) -> List[Tuple[date, str, str]]:
    """Return list of conflicts as (date, title_a, title_b) for each pair of events that share a date."""
    date_to_titles: dict[date, Set[str]] = {}
    for ev in events:
        for occ in occurrences(ev, start, end):
            date_to_titles.setdefault(occ, set()).add(ev.title)

    conflict_list: List[Tuple[date, str, str]] = []
    for d, titles in date_to_titles.items():
        if len(titles) < 2:
            continue
        sorted_titles = sorted(titles)
        for a, b in combinations(sorted_titles, 2):
            conflict_list.append((d, a, b))

    conflict_list.sort()
    return conflict_list