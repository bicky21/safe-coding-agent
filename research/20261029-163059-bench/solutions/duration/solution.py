import re

def parse_duration(s: str) -> int:
    if not isinstance(s, str):
        raise ValueError("Input must be a string")
    
    # Remove all spaces
    s = s.replace(" ", "")
    
    if not s:
        raise ValueError("Empty string is not a valid duration")
    
    # Define the pattern for a valid duration
    # Each part is a number followed by a unit
    # Units must appear in order: d, h, m, s
    # Each unit can appear at most once
    
    # We'll use a regex to match the entire string
    # The pattern should match:
    # - Optional days: \d+d
    # - Optional hours: \d+h
    # - Optional minutes: \d+m
    # - Optional seconds: \d+s
    # But at least one part must be present
    
    pattern = r'^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$'
    
    match = re.match(pattern, s, re.IGNORECASE)
    
    if not match:
        raise ValueError(f"Invalid duration format: {s}")
    
    # Check that at least one part is present
    if not any(match.groups()):
        raise ValueError("At least one unit is required")
    
    days = int(match.group(1)) if match.group(1) else 0
    hours = int(match.group(2)) if match.group(2) else 0
    minutes = int(match.group(3)) if match.group(3) else 0
    seconds = int(match.group(4)) if match.group(4) else 0
    
    total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
    
    return total_seconds