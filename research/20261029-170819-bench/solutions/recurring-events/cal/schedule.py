from datetime import date, timedelta
from typing import List, Tuple, Set
from .models import Event
from .rules import parse_rule, Rule, Weekday

def _add_months(orig: date, months: int) -> date:
    """Add months preserving day when possible, otherwise raise ValueError."""
    year = orig.year + (orig.month - 1 + months) // 12
    month = (orig.month - 1 + months) % 12 + 1
    day = orig.day
    # handle month length
    while True:
        try:
            return date(year, month, day)
        except ValueError:
            day -= 1
            if day == 0:
                raise

def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """Return the date of the nth weekday in a month. n>0 for 1st..4th, n==-1 for last."""
    if n > 0:
        # first day of month
        d = date(year, month, 1)
        # shift to first desired weekday
        shift = (weekday - d.weekday() + 7) % 7
        d += timedelta(days=shift + (n - 1) * 7)
        if d.month != month:
            raise ValueError("No such nth weekday")
        return d
    else:  # last
        # start from last day of month
        if month == 12:
            d = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            d = date(year, month + 1, 1) - timedelta(days=1)
        shift = (d.weekday() - weekday + 7) % 7
        d -= timedelta(days=shift)
        return d

def occurrences(event: Event, start: date, end: date) -> List[date]:
    """Return list of occurrence dates for event between start and end inclusive."""
    if start > end:
        return []

    rule_text = event.rule
    if not rule_text:
        # single occurrence
        occ = [event.start] if start <= event.start <= end else []
        return occ

    rule = parse_rule(rule_text)

    results: Set[date] = set()
    occ_count = 0
    cur = event.start

    # Helper to decide if we should stop
    def stop_condition(d: date) -> bool:
        if rule.until and d > rule.until:
            return True
        if rule.count is not None and occ_count >= rule.count:
            return True
        return False

    # Generate according to frequency
    if rule.freq == 'daily':
        while True:
            if cur >= event.start:
                if cur >= start and cur <= end and cur not in event.exceptions:
                    results.add(cur)
                occ_count += 1
            cur += timedelta(days=rule.interval)
            if stop_condition(cur):
                break

    elif rule.freq == 'weekly':
        # Determine week 0 Monday
        week0_monday = event.start - timedelta(days=event.start.weekday())
        week_index = 0
        while True:
            week_start = week0_monday + timedelta(weeks=week_index * rule.interval)
            days = rule.weekdays if rule.weekdays else [event.start.weekday()]
            for wd in days:
                occ = week_start + timedelta(days=wd)
                if occ < event.start:
                    continue
                if stop_condition(occ):
                    break
                if start <= occ <= end and occ not in event.exceptions:
                    results.add(occ)
                occ_count += 1
            week_index += 1
            # next week start check
            next_week = week0_monday + timedelta(weeks=week_index * rule.interval)
            if stop_condition(next_week):
                break

    elif rule.freq == 'monthly':
        month_index = 0
        while True:
            try:
                cur_month_date = _add_months(event.start, month_index * rule.interval)
            except ValueError:
                # impossible month (should not happen)
                break
            # Determine occurrence date for this month
            occ = None
            if rule.monthday:
                try:
                    occ = date(cur_month_date.year, cur_month_date.month, rule.monthday)
                except ValueError:
                    occ = None  # skip month without that day
            elif rule.nth is not None:
                try:
                    occ = _nth_weekday_of_month(cur_month_date.year,
                                                cur_month_date.month,
                                                rule.nth_weekday,
                                                rule.nth)
                except ValueError:
                    occ = None
            else:
                # default: same day as start
                try:
                    occ = date(cur_month_date.year, cur_month_date.month, event.start.day)
                except ValueError:
                    occ = None
            if occ and occ >= event.start:
                if stop_condition(occ):
                    break
                if start <= occ <= end and occ not in event.exceptions:
                    results.add(occ)
                occ_count += 1
            month_index += 1
            # stop if next month beyond end and no count limit
            next_month = _add_months(event.start, month_index * rule.interval)
            if next_month > end and rule.until is None and (rule.count is None or occ_count < rule.count):
                # still may need to stop by count, continue loop
                pass
            if rule.until and next_month > rule.until:
                break
            if rule.count is not None and occ_count >= rule.count:
                break

    elif rule.freq == 'yearly':
        year_index = 0
        while True:
            yr = event.start.year + year_index * rule.interval
            try:
                occ = date(yr, event.start.month, event.start.day)
            except ValueError:
                # e.g., Feb 29 on non‑leap year
                occ = None
            if occ and occ >= event.start:
                if stop_condition(occ):
                    break
                if start <= occ <= end and occ not in event.exceptions:
                    results.add(occ)
                occ_count += 1
            year_index += 1
            if rule.until and date(yr, 12, 31) > rule.until:
                break
            if rule.count is not None and occ_count >= rule.count:
                break
    else:
        raise ValueError(f"Unsupported frequency: {rule.freq}")

    return sorted(results)


def conflicts(events: List[Event], start: date, end: date) -> List[Tuple[date, str, str]]:
    """Return list of conflicts as (date, title_a, title_b) sorted."""
    occ_map: dict[date, List[str]] = {}
    for ev in events:
        for d in occurrences(ev, start, end):
            occ_map.setdefault(d, []).append(ev.title)

    conflict_list: List[Tuple[date, str, str]] = []
    for d, titles in occ_map.items():
        if len(titles) < 2:
            continue
        titles_sorted = sorted(titles)
        for i in range(len(titles_sorted)):
            for j in range(i + 1, len(titles_sorted)):
                conflict_list.append((d, titles_sorted[i], titles_sorted[j]))
    conflict_list.sort()
    return conflict_list