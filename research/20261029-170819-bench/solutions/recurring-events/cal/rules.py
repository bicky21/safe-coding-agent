import re
from datetime import date, timedelta
from typing import NamedTuple, Optional, List

Weekday = {
    'mon': 0, 'monday': 0,
    'tue': 1, 'tuesday': 1,
    'wed': 2, 'wednesday': 2,
    'thu': 3, 'thursday': 3,
    'fri': 4, 'friday': 4,
    'sat': 5, 'saturday': 5,
    'sun': 6, 'sunday': 6,
}


class Rule(NamedTuple):
    freq: str                     # 'daily','weekly','monthly','yearly'
    interval: int = 1
    weekdays: Optional[List[int]] = None          # for weekly
    monthday: Optional[int] = None                # for monthly by day
    nth: Optional[int] = None                     # 1,2,3,4 or -1 for last
    nth_weekday: Optional[int] = None             # weekday for nth rule
    until: Optional[date] = None
    count: Optional[int] = None


def _parse_until_or_count(text: str):
    """Return (remaining_text, until, count)"""
    until = None
    count = None
    m = re.search(r'\buntil\s+(\d{4}-\d{2}-\d{2})\b', text, re.I)
    if m:
        until = date.fromisoformat(m.group(1))
        text = text[:m.start()] + text[m.end():]
    m = re.search(r'\bfor\s+(\d+)\s+times\b', text, re.I)
    if m:
        count = int(m.group(1))
        text = text[:m.start()] + text[m.end():]
    return text.strip(), until, count


def parse_rule(text: str) -> Rule:
    """
    Parse a rule string into a Rule object.
    Raises ValueError on invalid syntax.
    """
    if not text or not text.strip():
        raise ValueError("Empty rule")

    original = text
    text = text.strip().lower()
    text, until, count = _parse_until_or_count(text)

    # daily
    m = re.fullmatch(r'(daily|every\s+(\d+)\s+days?)', text)
    if m:
        interval = 1
        if m.group(2):
            interval = int(m.group(2))
        if interval < 1:
            raise ValueError("Interval must be >=1")
        return Rule(freq='daily', interval=interval, until=until, count=count)

    # weekly
    m = re.fullmatch(r'(weekly|every\s+(\d+)\s+weeks?)(?:\s+on\s+([a-z,]+))?', text)
    if m:
        interval = 1
        if m.group(2):
            interval = int(m.group(2))
        if interval < 1:
            raise ValueError("Interval must be >=1")
        weekdays = None
        if m.group(3):
            days = [d.strip() for d in m.group(3).split(',')]
            weekdays = []
            for d in days:
                if d not in Weekday:
                    raise ValueError(f"Invalid weekday: {d}")
                weekdays.append(Weekday[d])
        return Rule(freq='weekly', interval=interval, weekdays=weekdays,
                    until=until, count=count)

    # monthly
    # patterns:
    #   monthly | every N months
    #   monthly on day D
    #   monthly on the last fri
    #   monthly on the 2nd tue
    #   every N months on day D / on the last fri / on the 3rd mon
    m = re.fullmatch(
        r'(monthly|every\s+(\d+)\s+months?)'
        r'(?:\s+on\s+'
        r'(?:day\s+(\d{1,2})|the\s+(1st|2nd|3rd|4th|last)\s+([a-z]+)))?', text)
    if m:
        interval = 1
        if m.group(2):
            interval = int(m.group(2))
        if interval < 1:
            raise ValueError("Interval must be >=1")
        monthday = None
        nth = None
        nth_weekday = None
        if m.group(3):  # day D
            monthday = int(m.group(3))
            if not (1 <= monthday <= 31):
                raise ValueError("Invalid month day")
        elif m.group(4):  # nth
            ord_map = {'1st': 1, '2nd': 2, '3rd': 3, '4th': 4, 'last': -1}
            nth = ord_map[m.group(4)]
            wk = m.group(5)
            if wk not in Weekday:
                raise ValueError(f"Invalid weekday: {wk}")
            nth_weekday = Weekday[wk]
        return Rule(freq='monthly', interval=interval,
                    monthday=monthday, nth=nth, nth_weekday=nth_weekday,
                    until=until, count=count)

    # yearly
    m = re.fullmatch(r'(yearly|every\s+(\d+)\s+years?)', text)
    if m:
        interval = 1
        if m.group(2):
            interval = int(m.group(2))
        if interval < 1:
            raise ValueError("Interval must be >=1")
        return Rule(freq='yearly', interval=interval, until=until, count=count)

    raise ValueError(f"Invalid rule text: {original}")