import re
from datetime import date, timedelta
from dataclasses import dataclass
from typing import Optional, List, Tuple

WEEKDAYS = {
    "mon": 0, "monday": 0,
    "tue": 1, "tuesday": 1,
    "wed": 2, "wednesday": 2,
    "thu": 3, "thursday": 3,
    "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5,
    "sun": 6, "sunday": 6,
}

ORDINALS = {
    "1st": 1, "first": 1,
    "2nd": 2, "second": 2,
    "3rd": 3, "third": 3,
    "4th": 4, "fourth": 4,
    "last": -1,
}

@dataclass
class Rule:
    freq: str                     # 'daily', 'weekly', 'monthly', 'yearly'
    interval: int = 1             # N
    weekdays: List[int] = None    # list of weekday indices
    monthday: Optional[int] = None  # day of month
    nth_weekday: Optional[Tuple[int, int]] = None  # (ordinal, weekday)
    until: Optional[date] = None
    times: Optional[int] = None   # number of occurrences

def _parse_until(text: str) -> Tuple[Optional[date], str]:
    m = re.search(r'\buntil\s+(\d{4}-\d{2}-\d{2})\b', text, re.I)
    if m:
        try:
            until_date = date.fromisoformat(m.group(1))
        except ValueError:
            raise ValueError("Invalid until date")
        text = text[:m.start()] + text[m.end():]
        return until_date, text.strip()
    return None, text

def _parse_times(text: str) -> Tuple[Optional[int], str]:
    m = re.search(r'\bfor\s+(\d+)\s+times\b', text, re.I)
    if m:
        times = int(m.group(1))
        if times < 1:
            raise ValueError("Times must be >= 1")
        text = text[:m.start()] + text[m.end():]
        return times, text.strip()
    return None, text

def _parse_weekdays(text: str) -> Tuple[Optional[List[int]], str]:
    m = re.search(r'\b(on|every)\s+([a-zA-Z,]+)\b', text, re.I)
    if m:
        days = [d.strip().lower() for d in m.group(2).split(',')]
        wds = []
        for d in days:
            if d not in WEEKDAYS:
                raise ValueError(f"Unknown weekday: {d}")
            wds.append(WEEKDAYS[d])
        text = text[:m.start()] + text[m.end():]
        return wds, text.strip()
    return None, text

def _parse_monthday(text: str) -> Tuple[Optional[int], str]:
    m = re.search(r'\bday\s+(\d{1,2})\b', text, re.I)
    if m:
        day = int(m.group(1))
        if not 1 <= day <= 31:
            raise ValueError("Day must be 1-31")
        text = text[:m.start()] + text[m.end():]
        return day, text.strip()
    return None, text

def _parse_nth_weekday(text: str) -> Tuple[Optional[Tuple[int, int]], str]:
    m = re.search(r'\b(on|every)\s+the\s+(1st|2nd|3rd|4th|last)\s+(mon|tue|wed|thu|fri|sat|sun)\b', text, re.I)
    if m:
        ordinal = ORDINALS[m.group(2).lower()]
        weekday = WEEKDAYS[m.group(3).lower()]
        text = text[:m.start()] + text[m.end():]
        return (ordinal, weekday), text.strip()
    return None, text

def parse_rule(text: str) -> Rule:
    if not text:
        raise ValueError("Empty rule")
    original = text
    text = text.lower().strip()
    until, text = _parse_until(text)
    times, text = _parse_times(text)
    weekdays, text = _parse_weekdays(text)
    monthday, text = _parse_monthday(text)
    nth_weekday, text = _parse_nth_weekday(text)

    # Frequency and interval
    freq = None
    interval = 1
    if text.startswith("daily"):
        freq = "daily"
        text = text[5:].strip()
    elif text.startswith("every"):
        m = re.match(r'every\s+(\d+)\s+(day|days|week|weeks|month|months|year|years)', text)
        if not m:
            raise ValueError(f"Invalid frequency in rule: {original}")
        interval = int(m.group(1))
        if interval < 1:
            raise ValueError("Interval must be >= 1")
        unit = m.group(2)
        if unit in ("day", "days"):
            freq = "daily"
        elif unit in ("week", "weeks"):
            freq = "weekly"
        elif unit in ("month", "months"):
            freq = "monthly"
        elif unit in ("year", "years"):
            freq = "yearly"
        else:
            raise ValueError("Unknown unit")
        text = text[m.end():].strip()
    else:
        raise ValueError(f"Unknown rule start: {original}")

    # Clean remaining text
    if text:
        raise ValueError(f"Unparsed rule part: '{text}'")

    return Rule(
        freq=freq,
        interval=interval,
        weekdays=weekdays,
        monthday=monthday,
        nth_weekday=nth_weekday,
        until=until,
        times=times,
    )