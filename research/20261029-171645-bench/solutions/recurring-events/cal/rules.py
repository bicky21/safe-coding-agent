import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

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


def _parse_until(text: str) -> Tuple[Optional[date], str]:
    m = re.search(r"\buntil\s+(\d{4}-\d{2}-\d{2})\b", text, re.IGNORECASE)
    if m:
        try:
            until = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError as e:
            raise ValueError(f"Invalid until date: {m.group(1)}") from e
        # remove the clause
        text = text[:m.start()] + text[m.end():]
        return until, text.strip()
    return None, text


def _parse_for(text: str) -> Tuple[Optional[int], str]:
    m = re.search(r"\bfor\s+(\d+)\s+times\b", text, re.IGNORECASE)
    if m:
        count = int(m.group(1))
        if count < 1:
            raise ValueError("Count must be >=1")
        text = text[:m.start()] + text[m.end():]
        return count, text.strip()
    return None, text


def _normalize(text: str) -> str:
    """
    Collapse multiple whitespace to a single space and remove spaces around commas.
    This makes the parser tolerant of irregular spacing like "Every  2   WEEKS on  Mon , fri".
    """
    # collapse whitespace
    text = re.sub(r"\s+", " ", text)
    # strip spaces around commas
    text = re.sub(r"\s*,\s*", ",", text)
    return text.strip()


def parse_rule(text: str) -> Dict[str, Any]:
    """
    Parse a rule string into a dictionary describing the recurrence.
    The dictionary contains at least a 'freq' key (daily, weekly, monthly, yearly)
    and may contain other keys such as 'interval', 'weekdays', 'monthday',
    'nth', 'weekday', 'until', 'count'.
    """
    if not text or not text.strip():
        raise ValueError("Empty rule")

    original = text
    # case‑insensitive handling and tolerant whitespace
    text = text.lower()
    text = _normalize(text)

    # extract optional ending clauses
    until, text = _parse_until(text)
    count, text = _parse_for(text)

    # daily
    m = re.fullmatch(r"(daily|every\s+(\d+)\s+days?)", text)
    if m:
        interval = 1
        if m.group(2):
            interval = int(m.group(2))
        if interval < 1:
            raise ValueError("Interval must be >=1")
        return {"freq": "daily", "interval": interval, "until": until, "count": count}

    # weekly
    m = re.fullmatch(r"(weekly|every\s+(\d+)\s+weeks?)(?:\s+on\s+([a-z,]+))?", text)
    if m:
        interval = 1
        if m.group(2):
            interval = int(m.group(2))
        if interval < 1:
            raise ValueError("Interval must be >=1")
        weekdays = None
        if m.group(3):
            days = [d.strip() for d in m.group(3).split(",")]
            weekdays = []
            for d in days:
                if d not in WEEKDAYS:
                    raise ValueError(f"Invalid weekday: {d}")
                weekdays.append(WEEKDAYS[d])
        return {
            "freq": "weekly",
            "interval": interval,
            "weekdays": weekdays,   # None means the weekday of start date
            "until": until,
            "count": count,
        }

    # monthly
    m = re.fullmatch(
        r"(monthly|every\s+(\d+)\s+months?)(?:\s+on\s+(.+))?", text
    )
    if m:
        interval = 1
        if m.group(2):
            interval = int(m.group(2))
        if interval < 1:
            raise ValueError("Interval must be >=1")
        on_part = m.group(3)
        rule: Dict[str, Any] = {
            "freq": "monthly",
            "interval": interval,
            "until": until,
            "count": count,
        }
        if not on_part:
            rule["type"] = "day_of_month"
            return rule

        on_part = on_part.strip()
        # day number
        m_day = re.fullmatch(r"day\s+(\d{1,2})", on_part)
        if m_day:
            d = int(m_day.group(1))
            if not (1 <= d <= 31):
                raise ValueError("Day must be 1..31")
            rule["type"] = "day_of_month"
            rule["day"] = d
            return rule

        # nth weekday e.g. "the 2nd tue"
        m_nth = re.fullmatch(r"the\s+(1st|first|2nd|second|3rd|third|4th|fourth|last)\s+([a-z]+)", on_part)
        if m_nth:
            ord_str = m_nth.group(1)
            wkday = m_nth.group(2)
            if wkday not in WEEKDAYS:
                raise ValueError(f"Invalid weekday: {wkday}")
            rule["type"] = "nth_weekday"
            rule["ordinal"] = ORDINALS[ord_str]
            rule["weekday"] = WEEKDAYS[wkday]
            return rule

        raise ValueError(f"Invalid monthly on-part: {on_part}")

    # yearly
    m = re.fullmatch(r"(yearly|every\s+(\d+)\s+years?)(?:\s+on\s+(.+))?", text)
    if m:
        interval = 1
        if m.group(2):
            interval = int(m.group(2))
        if interval < 1:
            raise ValueError("Interval must be >=1")
        # yearly always uses month/day of start, optional extra on-part not supported
        return {
            "freq": "yearly",
            "interval": interval,
            "until": until,
            "count": count,
        }

    raise ValueError(f"Unrecognised rule: {original}")