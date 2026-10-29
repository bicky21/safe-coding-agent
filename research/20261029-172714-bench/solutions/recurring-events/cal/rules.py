"""
Simple rule parser for recurring events.
"""

import re
from datetime import date
from dataclasses import dataclass
from typing import Optional, List, Tuple

# --------------------------------------------------------------------------- #
#   Helpers
# --------------------------------------------------------------------------- #

WEEKDAY_MAP = {
    "mon": 0, "monday": 0,
    "tue": 1, "tues": 1, "tuesday": 1,
    "wed": 2, "wednesday": 2,
    "thu": 3, "thurs": 3, "thursday": 3,
    "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5,
    "sun": 6, "sunday": 6,
}

ORDINAL_MAP = {
    "1st": 1, "first": 1,
    "2nd": 2, "second": 2,
    "3rd": 3, "third": 3,
    "4th": 4, "fourth": 4,
    "last": -1,
}

# --------------------------------------------------------------------------- #
#   Rule data structure
# --------------------------------------------------------------------------- #

@dataclass
class Rule:
    freq: str                     # "daily", "weekly", "monthly", "yearly"
    interval: int = 1             # N in every N ...
    weekdays: Optional[List[int]] = None   # list of weekday numbers 0-6
    monthday: Optional[int] = None         # day of month 1-31
    nth_weekday: Optional[Tuple[int, int]] = None  # (ordinal, weekday)
    until: Optional[date] = None
    count: Optional[int] = None   # number of occurrences

# --------------------------------------------------------------------------- #
#   Parsing helpers
# --------------------------------------------------------------------------- #

def _split_and_normalize(text: str) -> str:
    return " ".join(text.strip().split()).lower()

def _extract_until(text: str) -> Tuple[Optional[date], str]:
    m = re.search(r"\buntil\s+(\d{4}-\d{2}-\d{2})\b", text)
    if m:
        until_date = date.fromisoformat(m.group(1))
        text = text[:m.start()] + text[m.end():]
        return until_date, text.strip()
    return None, text

def _extract_count(text: str) -> Tuple[Optional[int], str]:
    m = re.search(r"\bfor\s+(\d+)\s+times\b", text)
    if m:
        count = int(m.group(1))
        text = text[:m.start()] + text[m.end():]
        return count, text.strip()
    return None, text

def _extract_weekdays(text: str) -> Tuple[Optional[List[int]], str]:
    m = re.search(r"\bon\s+([a-zA-Z,]+)\b", text)
    if m:
        days = [d.strip() for d in m.group(1).split(",")]
        wds = []
        for d in days:
            if d not in WEEKDAY_MAP:
                raise ValueError(f"Unknown weekday: {d}")
            wds.append(WEEKDAY_MAP[d])
        text = text[:m.start()] + text[m.end():]
        return wds, text.strip()
    return None, text

def _extract_nth_weekday(text: str) -> Tuple[Optional[Tuple[int, int]], str]:
    m = re.search(r"\bon\s+the\s+(\w+)\s+(\w+)\b", text)
    if m:
        ordinal_str, weekday_str = m.group(1).lower(), m.group(2).lower()
        if ordinal_str not in ORDINAL_MAP:
            raise ValueError(f"Unknown ordinal: {ordinal_str}")
        if weekday_str not in WEEKDAY_MAP:
            raise ValueError(f"Unknown weekday: {weekday_str}")
        ordinal = ORDINAL_MAP[ordinal_str]
        weekday = WEEKDAY_MAP[weekday_str]
        text = text[:m.start()] + text[m.end():]
        return (ordinal, weekday), text.strip()
    return None, text

def _extract_monthday(text: str) -> Tuple[Optional[int], str]:
    m = re.search(r"\bon\s+day\s+(\d{1,2})\b", text)
    if m:
        day = int(m.group(1))
        if not 1 <= day <= 31:
            raise ValueError("Month day must be 1-31")
        text = text[:m.start()] + text[m.end():]
        return day, text.strip()
    return None, text

# --------------------------------------------------------------------------- #
#   Main parser
# --------------------------------------------------------------------------- #

def parse_rule(text: str) -> Rule:
    if not text:
        raise ValueError("Empty rule")
    text = _split_and_normalize(text)

    # Optional ending clauses
    until, text = _extract_until(text)
    count, text = _extract_count(text)

    # Frequency & interval
    freq = None
    interval = 1
    if text.startswith("daily"):
        freq = "daily"
        text = text[5:].strip()
    elif text.startswith("weekly"):
        freq = "weekly"
        text = text[6:].strip()
    elif text.startswith("monthly"):
        freq = "monthly"
        text = text[7:].strip()
    elif text.startswith("yearly"):
        freq = "yearly"
        text = text[6:].strip()
    elif text.startswith("every"):
        m = re.match(r"every\s+(\d+)\s+days", text)
        if m:
            interval = int(m.group(1))
            freq = "daily"
            text = text[m.end():].strip()
        else:
            m = re.match(r"every\s+(\d+)\s+weeks", text)
            if m:
                interval = int(m.group(1))
                freq = "weekly"
                text = text[m.end():].strip()
            else:
                m = re.match(r"every\s+(\d+)\s+months", text)
                if m:
                    interval = int(m.group(1))
                    freq = "monthly"
                    text = text[m.end():].strip()
                else:
                    m = re.match(r"every\s+(\d+)\s+years", text)
                    if m:
                        interval = int(m.group(1))
                        freq = "yearly"
                        text = text[m.end():].strip()
                    else:
                        raise ValueError("Unknown frequency")
    else:
        raise ValueError("Unknown frequency")

    if not freq:
        raise ValueError("Frequency not determined")

    # Optional modifiers
    weekdays, text = _extract_weekdays(text)
    nth_weekday, text = _extract_nth_weekday(text)
    monthday, text = _extract_monthday(text)

    # Remaining text must be empty
    if text:
        raise ValueError(f"Unparsed rule part: '{text}'")

    # Validate combinations
    if freq == "daily" and (weekdays or monthday or nth_weekday):
        raise ValueError("Daily rule cannot have weekdays/monthday/nth_weekday")
    if freq == "weekly" and not weekdays:
        weekdays = []
    if freq == "monthly" and not (monthday or nth_weekday):
        # default to event.start day
        pass
    if freq == "yearly" and (weekdays or monthday or nth_weekday):
        raise ValueError("Yearly rule cannot have weekdays/monthday/nth_weekday")

    return Rule(
        freq=freq,
        interval=interval,
        weekdays=weekdays,
        monthday=monthday,
        nth_weekday=nth_weekday,
        until=until,
        count=count,
    )