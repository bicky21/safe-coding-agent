"""
Occurrence generation and conflict detection for events.
"""

from datetime import date, timedelta
from typing import List, Tuple
from .models import Event
from .rules import Rule, parse_rule

# --------------------------------------------------------------------------- #
#   Utility helpers
# --------------------------------------------------------------------------- #

def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - date(year, month, 1)).days

def _add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, _days_in_month(year, month))
    return date(year, month, day)

def _nth_weekday_of_month(year: int, month: int, weekday: int, nth: int) -> date:
    # nth > 0: first, second, etc.
    # nth == -1: last
    first = date(year, month, 1)
    first_weekday = first.weekday()
    delta = (weekday - first_weekday) % 7
    if nth > 0:
        day = 1 + delta + (nth - 1) * 7
        if day > _days_in_month(year, month):
            raise ValueError("No such date")
        return date(year, month, day)
    # last
    last_day = _days_in_month(year, month)
    last_date = date(year, month, last_day)
    last_weekday = last_date.weekday()
    delta = (last_weekday - weekday) % 7
    day = last_day - delta
    return date(year, month, day)

# --------------------------------------------------------------------------- #
#   Occurrence generation
# --------------------------------------------------------------------------- #

def occurrences(event: Event, start: date, end: date) -> List[date]:
    """
    Return list of dates on which the event occurs between start and end (inclusive).
    """
    if event.rule is None:
        if event.start < start or event.start > end:
            return []
        return [event.start]

    rule = parse_rule(event.rule)
    result: List[date] = []

    # Start from event.start
    current = event.start

    # Helper to add occurrence if valid
    def add_occ(d: date):
        if start <= d <= end and d not in event.exceptions:
            result.append(d)

    # Count of occurrences generated so far (including those before the start date)
    generated_count = 0

    # Loop until we pass end or reach limits
    while True:
        if current > end:
            break
        # Skip dates before event.start
        if current >= event.start:
            # Determine if current date matches rule
            if rule.freq == "daily":
                add_occ(current)
            elif rule.freq == "weekly":
                # For each weekday in this week
                week_start = current - timedelta(days=current.weekday())
                weekdays = rule.weekdays or [event.start.weekday()]
                for wd in weekdays:
                    occ_date = week_start + timedelta(days=wd)
                    if occ_date < event.start:
                        continue
                    if occ_date > end:
                        continue
                    if occ_date < start:
                        continue
                    if occ_date not in event.exceptions:
                        result.append(occ_date)
            elif rule.freq == "monthly":
                # Determine occurrence date for this month
                if rule.monthday:
                    try:
                        occ_date = date(current.year, current.month, rule.monthday)
                    except ValueError:
                        occ_date = None
                elif rule.nth_weekday:
                    try:
                        occ_date = _nth_weekday_of_month(
                            current.year, current.month,
                            rule.nth_weekday[1], rule.nth_weekday[0]
                        )
                    except ValueError:
                        occ_date = None
                else:
                    # default to event.start day
                    try:
                        occ_date = date(current.year, current.month, event.start.day)
                    except ValueError:
                        occ_date = None
                if occ_date and start <= occ_date <= end and occ_date not in event.exceptions:
                    result.append(occ_date)
            elif rule.freq == "yearly":
                try:
                    occ_date = date(current.year, event.start.month, event.start.day)
                except ValueError:
                    # Handle Feb 29
                    if event.start.month == 2 and event.start.day == 29:
                        # Skip non-leap years
                        occ_date = None
                    else:
                        occ_date = None
                if occ_date and start <= occ_date <= end and occ_date not in event.exceptions:
                    result.append(occ_date)

        # Increment generated_count only for dates that are >= event.start
        if current >= event.start:
            generated_count += 1

        # Check limits
        if rule.until and current >= rule.until:
            break
        if rule.count and generated_count >= rule.count:
            break

        # Advance to next cycle
        if rule.freq == "daily":
            current += timedelta(days=rule.interval)
        elif rule.freq == "weekly":
            # Move to the Monday of the next cycle
            current = current + timedelta(weeks=rule.interval)
            current = current - timedelta(days=current.weekday())
        elif rule.freq == "monthly":
            current = _add_months(current, rule.interval)
        elif rule.freq == "yearly":
            try:
                current = date(current.year + rule.interval, event.start.month, event.start.day)
            except ValueError:
                # Skip invalid Feb 29
                current = date(current.year + rule.interval, 3, 1)

    # Remove duplicates and sort
    return sorted(set(result))

# --------------------------------------------------------------------------- #
#   Conflict detection
# --------------------------------------------------------------------------- #

def conflicts(events: List[Event], start: date, end: date) -> List[Tuple[date, str, str]]:
    """
    Return list of conflicts as (date, title_a, title_b) where title_a < title_b.
    """
    occ_map: dict[date, List[str]] = {}
    for ev in events:
        for d in occurrences(ev, start, end):
            occ_map.setdefault(d, []).append(ev.title)

    result: List[Tuple[date, str, str]] = []
    for d, titles in occ_map.items():
        if len(titles) > 1:
            titles = sorted(set(titles))
            for i in range(len(titles)):
                for j in range(i + 1, len(titles)):
                    result.append((d, titles[i], titles[j]))
    return sorted(result)