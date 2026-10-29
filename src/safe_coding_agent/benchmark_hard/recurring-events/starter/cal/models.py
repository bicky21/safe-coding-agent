from dataclasses import dataclass, field
from datetime import date


@dataclass
class Event:
    title: str
    start: date
    rule: str | None = None                      # e.g. "every 2 weeks on mon,fri until 2026-12-31"
    exceptions: set[date] = field(default_factory=set)
