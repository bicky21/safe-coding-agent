from datetime import date, timedelta
from typing import List, Tuple
from .models import Event
from .rules import parse_rule, Rule

def _add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, [31,
        29 if year%4==0 and (year%100!=0 or year%400==0) else 28,
        31,30,31,30,31,31,30,31,30,31][month-1])
    return date(year, month, day)

def _nth_weekday_of_month(year: int, month: int, weekday: int, nth: int) -> date:
    if nth > 0:
        d = date(year, month, 1)
        offset = (weekday - d.weekday() + 7) % 7
        day = 1 + offset + (nth - 1) * 7
        if day > (date(year, month, 28) + timedelta(days=4)).day:
            raise ValueError
        return date(year, month, day)
    else:  # last
        d = date(year, month, 1)
        last_day = (date(year, month, 28) + timedelta(days=4)).day
        offset = (d.weekday() - weekday + 7) % 7
        day = last_day - offset
        return date(year, month, day)

def _generate_occurrences(event: Event, start: date, end: date) -> List[date]:
    if event.rule is None:
        if event.start < start or event.start > end:
            return []
        return [event.start]
    rule = parse_rule(event.rule)
    results = []
    current = event.start
    count = 0
    while True:
        if current > end:
            break
        if current >= start:
            if current not in event.exceptions:
                results.append(current)
            count += 1
        # stop conditions
        if rule.until and current >= rule.until:
            break
        if rule.times and count >= rule.times:
            break
        # advance
        if rule.freq == "daily":
            current += timedelta(days=rule.interval)
        elif rule.freq == "weekly":
            # find next week start
            days_ahead = (7 * rule.interval) - ((current - event.start).days % (7 * rule.interval))
            current += timedelta(days=days_ahead)
        elif rule.freq == "monthly":
            current = _add_months(current, rule.interval)
        elif rule.freq == "yearly":
            try:
                current = date(current.year + rule.interval, current.month, current.day)
            except ValueError:
                # skip non-leap year Feb 29
                current = date(current.year + rule.interval, 3, 1)
        else:
            break
    # filter by rule specifics
    filtered = []
    for d in results:
        if rule.weekdays and d.weekday() not in rule.weekdays:
            continue
        if rule.monthday and d.day != rule.monthday:
            continue
        if rule.nth_weekday:
            nth, wd = rule.nth_weekday
            try:
                target = _nth_weekday_of_month(d.year, d.month, wd, nth)
            except Exception:
                continue
            if target != d:
                continue
        filtered.append(d)
    return sorted(set(filtered))

def occurrences(event: Event, start: date, end: date) -> List[date]:
    return _generate_occurrences(event, start, end)

def conflicts(events: List[Event], start: date, end: date) -> List[Tuple[date, str, str]]:
    occ_map = {}
    for ev in events:
        for d in occurrences(ev, start, end):
            occ_map.setdefault(d, []).append(ev.title)
    result = []
    for d, titles in sorted(occ_map.items()):
        if len(titles) > 1:
            titles = sorted(titles)
            for i in range(len(titles)):
                for j in range(i+1, len(titles)):
                    result.append((d, titles[i], titles[j]))
    return result