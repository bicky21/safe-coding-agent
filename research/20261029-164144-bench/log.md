# Run log

Settings: {"model": "openai:openai/gpt-oss-20b", "max_attempts": 3, "feedback": "detailed", "anti_stuck": true, "plan_first": false, "safety": "task default"}

Runner: local

## brackets (medium): passed, best 6/6 tests

### Attempt 1: passed (6/6 tests, 1.6s)

File `solution.py`:

```python
def is_balanced(s: str) -> bool:
    """
    Return True if every bracket in the string `s` is correctly opened and closed.
    Brackets considered are: (), [], {}. All other characters are ignored.

    Parameters
    ----------
    s : str
        The input string to check for balanced brackets.

    Returns
    -------
    bool
        True if brackets are balanced, False otherwise.
    """
    # Mapping of closing to opening brackets
    pairs = {')': '(', ']': '[', '}': '{'}
    # Stack to keep track of opening brackets
    stack = []

    for ch in s:
        if ch in pairs.values():  # opening bracket
            stack.append(ch)
        elif ch in pairs:  # closing bracket
            if not stack or stack[-1] != pairs[ch]:
                return False
            stack.pop()

    # If stack is empty, all brackets were matched
    return not stack
```

Feedback:

```
all tests passed
```


## dijkstra (hard): passed, best 4/4 tests

### Attempt 1: passed (4/4 tests, 1.5s)

File `solution.py`:

```python
import heapq
from typing import List, Tuple

def shortest_paths(n: int, edges: List[Tuple[int, int, int]], src: int) -> List[float]:
    """
    Compute the shortest distances from a source node to all other nodes in a directed
    graph with non-negative edge weights using Dijkstra's algorithm.

    Parameters
    ----------
    n : int
        Number of nodes in the graph. Nodes are labeled from 0 to n-1.
    edges : List[Tuple[int, int, int]]
        List of directed edges represented as (u, v, weight). All weights are
        assumed to be non-negative.
    src : int
        The source node from which shortest paths are computed.

    Returns
    -------
    List[float]
        A list of length n where the i-th element is the shortest distance from
        src to node i. If a node is unreachable, its distance is float('inf').
    """
    # Edge case: empty graph
    if n == 0:
        return []

    # Build adjacency list
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        # Validate indices (optional, but safe)
        if 0 <= u < n and 0 <= v < n:
            adj[u].append((v, w))

    # Initialize distances
    dist = [float('inf')] * n
    dist[src] = 0.0

    # Min-heap priority queue: (distance, node)
    heap = [(0.0, src)]

    while heap:
        d, u = heapq.heappop(heap)

        # If we have already found a better path to u, skip
        if d > dist[u]:
            continue

        for v, w in adj[u]:
            new_dist = d + w
            if new_dist < dist[v]:
                dist[v] = new_dist
                heapq.heappush(heap, (new_dist, v))

    return dist
```

Feedback:

```
all tests passed
```


## duration (tricky): passed, best 12/12 tests

### Attempt 1: invalid (0/0 tests, 5.5s)

Feedback:

````
Your answer could not be used: no files found in your answer.

Return every file you create or change in exactly this format,
with the FULL file content (no "..." placeholders):

FILE: path/to/file.py
```python
<full content of the file>
```

Do not change anything in tests/. Do not use input(), the network, or shell commands.
````

Raw model reply (could not be used):

````text
FILE: solution.py
```python
"""
Utility module for parsing duration strings into total seconds.

The main function `parse_duration` accepts a string representation of a duration
(e.g., "1h30m", "2d 3h", "45s") and returns the total number of seconds as an
integer. The function enforces strict formatting rules:

* Units are d, h, m, s (case‑insensitive).
* Each unit may appear at most once and must appear in the order d → h → m → s.
* Spaces between parts are allowed but otherwise the string must consist
  solely of number–unit pairs.
* Any deviation from these rules raises a ValueError.

Examples
--------
>>> parse_duration("1h30m")
5400
>>> parse_duration("2d 3h")
183600
>>> parse_duration("45s")
45
"""

import re
from typing import Dict

# Mapping of unit to its multiplier in seconds
_UNIT_MULTIPLIERS: Dict[str, int] = {
    'd': 86400,
    'h': 3600,
    'm': 60,
    's': 1,
}

# Ordered list of units to enforce correct sequence
_UNIT_ORDER: Dict[str, int] = {unit: idx for idx, unit in enumerate('dhms')}


def parse_duration(s: str) -> int:
    """
    Convert a duration string into total seconds.

    Parameters
    ----------
    s : str
        Duration string (e.g., "1h30m", "2d 3h", "45s").

    Returns
    -------
    int
        Total duration in seconds.

    Raises
    ------
    ValueError
        If the input string is empty, contains invalid characters,
        has units out of order, repeats a unit, or otherwise does not
        conform to the expected format.
    """
    if not isinstance(s, str):
        raise ValueError("Input must be a string")

    # Strip leading/trailing whitespace and ensure non‑empty
    stripped = s.strip()
    if not stripped:
        raise ValueError("Empty duration string")

    # Remove all spaces for easier processing
    compact = ''.join(stripped.split())

    # Regular expression to capture number + unit pairs
    pattern = re.compile(r'(\d+)([dhmsDHMS])')
    matches = list(pattern.finditer(compact))

    if not matches:
        raise ValueError("No valid duration parts found")

    # Reconstruct the string from matches and compare to the compact input
    matched_str = ''.join(m.group(0) for m in matches)
    if matched_str != compact:
        raise ValueError("Invalid format or stray characters")

    total_seconds = 0
    seen_units = set()
    prev_index = -1

    for match in matches:
        number_str, unit_raw = match.group(1), match.group(2)
        unit = unit_raw.lower()

        # Validate unit
        if unit not in _UNIT_MULTIPLIERS:
            raise ValueError(f"Unknown unit: {unit}")

        # Check for repeated units
        if unit in seen_units:
            raise ValueError(f"Repeated unit: {unit}")
        seen_units.add(unit)

        # Enforce correct order
        current_index = _UNIT_ORDER[unit]
        if current_index <= prev_index:
            raise Value
````


### Attempt 2: failed (11/12 tests, 4.0s)

File `solution.py`:

```python
import re

# Regular expression to match the duration string.
# It allows optional whitespace between parts and is case-insensitive.
# The order of units is enforced by the order of optional groups.
_DUR_PATTERN = re.compile(
    r"""
    ^\s*                                   # Optional leading whitespace
    (?:(?P<days>\d+)\s*d\s*)?              # Optional days
    (?:(?P<hours>\d+)\s*h\s*)?             # Optional hours
    (?:(?P<minutes>\d+)\s*m\s*)?           # Optional minutes
    (?:(?P<seconds>\d+)\s*s\s*)?           # Optional seconds
    \s*$                                   # Optional trailing whitespace
    """,
    re.IGNORECASE | re.VERBOSE
)

def parse_duration(s: str) -> int:
    """
    Convert a duration string into total seconds.

    Parameters
    ----------
    s : str
        Duration string, e.g. '1h30m', '2d 4h', '45s', etc.
        Units are d (days), h (hours), m (minutes), s (seconds).
        Units are case-insensitive and may appear at most once
        in the order d, h, m, s. Spaces between parts are allowed.

    Returns
    -------
    int
        Total number of seconds represented by the duration.

    Raises
    ------
    ValueError
        If the string is empty, does not contain any unit,
        contains a unit without a preceding number, contains
        repeated units, or has units out of order.
    """
    if not isinstance(s, str):
        raise ValueError("Input must be a string")

    match = _DUR_PATTERN.fullmatch(s)
    if not match:
        raise ValueError(f"Invalid duration format: {s!r}")

    # Extract groups; if a group is missing, default to 0
    days = int(match.group('days')) if match.group('days') else 0
    hours = int(match.group('hours')) if match.group('hours') else 0
    minutes = int(match.group('minutes')) if match.group('minutes') else 0
    seconds = int(match.group('seconds')) if match.group('seconds') else 0

    # Compute total seconds
    total_seconds = (
        days * 86400 +
        hours * 3600 +
        minutes * 60 +
        seconds
    )

    return total_seconds
```

Feedback:

```
11 of 12 tests passed.
=================================== FAILURES ===================================
____________________________ test_invalid_raises[] _____________________________
tests/test_duration.py:15: in test_invalid_raises
    with pytest.raises(ValueError):
         ^^^^^^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE ValueError
=========================== short test summary info ============================
FAILED tests/test_duration.py::test_invalid_raises[] - Failed: DID NOT RAISE ValueError
========================= 1 failed, 11 passed in 0.03s =========================
```


### Attempt 3: passed (12/12 tests, 2.1s)

File `solution.py`:

```python
import re

# Regular expression to match the duration string.
# It allows optional whitespace between parts and is case-insensitive.
# The order of units is enforced by the order of optional groups.
_DUR_PATTERN = re.compile(
    r"""
    ^\s*                                   # Optional leading whitespace
    (?:(?P<days>\d+)\s*d\s*)?              # Optional days
    (?:(?P<hours>\d+)\s*h\s*)?             # Optional hours
    (?:(?P<minutes>\d+)\s*m\s*)?           # Optional minutes
    (?:(?P<seconds>\d+)\s*s\s*)?           # Optional seconds
    \s*$                                   # Optional trailing whitespace
    """,
    re.IGNORECASE | re.VERBOSE
)

def parse_duration(s: str) -> int:
    """
    Convert a duration string into total seconds.

    Parameters
    ----------
    s : str
        Duration string, e.g. '1h30m', '2d 4h', '45s', etc.
        Units are d (days), h (hours), m (minutes), s (seconds).
        Units are case-insensitive and may appear at most once
        in the order d, h, m, s. Spaces between parts are allowed.

    Returns
    -------
    int
        Total number of seconds represented by the duration.

    Raises
    ------
    ValueError
        If the string is empty, does not contain any unit,
        contains a unit without a preceding number, contains
        repeated units, or has units out of order.
    """
    if not isinstance(s, str):
        raise ValueError("Input must be a string")

    match = _DUR_PATTERN.fullmatch(s)
    if not match:
        raise ValueError(f"Invalid duration format: {s!r}")

    # Ensure that at least one unit is present
    if not any(match.group(g) for g in ('days', 'hours', 'minutes', 'seconds')):
        raise ValueError(f"Duration string must contain at least one unit: {s!r}")

    # Extract groups; if a group is missing, default to 0
    days = int(match.group('days')) if match.group('days') else 0
    hours = int(match.group('hours')) if match.group('hours') else 0
    minutes = int(match.group('minutes')) if match.group('minutes') else 0
    seconds = int(match.group('seconds')) if match.group('seconds') else 0

    # Compute total seconds
    total_seconds = (
        days * 86400 +
        hours * 3600 +
        minutes * 60 +
        seconds
    )

    return total_seconds
```

Feedback:

```
all tests passed
```


## intervals (medium): passed, best 5/5 tests

### Attempt 1: passed (5/5 tests, 35.7s)

File `solution.py`:

```python
"""
Solution for merging overlapping or touching intervals.

The function `merge_intervals` takes a list of intervals, where each interval is
represented as a two-element list `[start, end]`. It merges all intervals that
overlap or touch (i.e., where the end of one interval is greater than or equal
to the start of the next) and returns a new list of merged intervals sorted
by their start values.

Example:
    >>> merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]])
    [[1, 6], [8, 10], [15, 18]]
"""

from __future__ import annotations

from typing import List


def merge_intervals(intervals: List[List[int]]) -> List[List[int]]:
    """
    Merge all overlapping or touching intervals.

    Parameters
    ----------
    intervals : List[List[int]]
        A list of intervals, each represented as a list of two integers
        `[start, end]`. The list may be unsorted and may contain duplicate
        or nested intervals.

    Returns
    -------
    List[List[int]]
        A new list of merged intervals sorted by start value. Each interval
        is represented as a list `[start, end]`.

    Notes
    -----
    - Intervals that only touch (e.g., `[1, 2]` and `[2, 3]`) are merged.
    - If the input list is empty, an empty list is returned.
    - The function does not modify the input list.
    """
    if not intervals:
        return []

    # Sort intervals by start value. If starts are equal, sort by end.
    sorted_intervals = sorted(intervals, key=lambda x: (x[0], x[1]))

    merged: List[List[int]] = []
    current_start, current_end = sorted_intervals[0]

    for start, end in sorted_intervals[1:]:
        # If the current interval overlaps or touches the next one,
        # extend the current interval's end if necessary.
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            # No overlap; append the current interval and start a new one.
            merged.append([current_start, current_end])
            current_start, current_end = start, end

    # Append the last interval.
    merged.append([current_start, current_end])

    return merged
```

Feedback:

```
all tests passed
```


## lcs (medium): passed, best 4/4 tests

### Attempt 1: passed (4/4 tests, 3.1s)

File `solution.py`:

```python
"""
Longest Common Subsequence implementation using dynamic programming.

The function `lcs(a: str, b: str) -> str` returns one longest common subsequence
of the two input strings `a` and `b`.  If there are multiple LCSs of the same
maximum length, any one of them may be returned.

The algorithm runs in O(len(a) * len(b)) time and uses O(len(a) * len(b))
additional memory for the DP table.
"""

from typing import List


def lcs(a: str, b: str) -> str:
    """
    Return one longest common subsequence of strings `a` and `b`.

    Parameters
    ----------
    a : str
        First input string.
    b : str
        Second input string.

    Returns
    -------
    str
        A string that is a longest common subsequence of `a` and `b`.
        If either input is empty, the empty string is returned.
    """
    # Edge cases: if either string is empty, the LCS is empty.
    if not a or not b:
        return ""

    n, m = len(a), len(b)

    # dp[i][j] will hold the length of the LCS of a[:i] and b[:j]
    dp: List[List[int]] = [[0] * (m + 1) for _ in range(n + 1)]

    # Fill the DP table
    for i in range(1, n + 1):
        ai = a[i - 1]
        for j in range(1, m + 1):
            if ai == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # Reconstruct one LCS by walking backwards through the DP table
    i, j = n, m
    lcs_chars: List[str] = []

    while i > 0 and j > 0:
        if a[i - 1] == b[j - 1]:
            # Characters match; part of the LCS
            lcs_chars.append(a[i - 1])
            i -= 1
            j -= 1
        else:
            # Move in the direction of the larger DP value
            if dp[i - 1][j] >= dp[i][j - 1]:
                i -= 1
            else:
                j -= 1

    # The characters were collected in reverse order
    lcs_chars.reverse()
    return "".join(lcs_chars)
```

Feedback:

```
all tests passed
```


## lru (hard): passed, best 7/7 tests

### Attempt 1: passed (7/7 tests, 2.5s)

File `solution.py`:

```python
from collections import OrderedDict

class LRUCache:
    """
    Least Recently Used (LRU) cache implementation.

    Attributes
    ----------
    capacity : int
        Maximum number of items the cache can hold.
    cache : OrderedDict
        Stores key-value pairs in order of usage, with the most recently used
        item at the end.
    """

    def __init__(self, capacity: int):
        """
        Initialize the LRU cache with a given capacity.

        Parameters
        ----------
        capacity : int
            The maximum number of key-value pairs the cache can store.
        """
        if capacity <= 0:
            raise ValueError("Capacity must be a positive integer")
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key: int) -> int:
        """
        Retrieve the value associated with the given key.

        If the key exists, it is marked as recently used.
        If the key does not exist, return -1.

        Parameters
        ----------
        key : int
            The key to look up.

        Returns
        -------
        int
            The value associated with the key, or -1 if the key is not present.
        """
        if key not in self.cache:
            return -1
        # Move the key to the end to mark it as recently used
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: int, value: int) -> None:
        """
        Insert or update the value for a key in the cache.

        If the key already exists, its value is updated and it is marked as
        recently used. If the key does not exist and the cache is at capacity,
        the least recently used item is evicted before inserting the new item.

        Parameters
        ----------
        key : int
            The key to insert or update.
        value : int
            The value to associate with the key.
        """
        if key in self.cache:
            # Update existing key and mark as recently used
            self.cache.move_to_end(key)
            self.cache[key] = value
            return

        if len(self.cache) >= self.capacity:
            # Evict the least recently used item (first item in OrderedDict)
            self.cache.popitem(last=False)

        self.cache[key] = value
```

Feedback:

```
all tests passed
```


## palindrome (easy): passed, best 4/4 tests

### Attempt 1: passed (4/4 tests, 13.6s)

File `solution.py`:

```python
def is_palindrome(s: str) -> bool:
    """
    Return True if the input string s is a palindrome, ignoring case,
    spaces, and punctuation. Non-alphanumeric characters are removed
    before comparison.

    Parameters
    ----------
    s : str
        The string to check.

    Returns
    -------
    bool
        True if s is a palindrome under the described conditions, False otherwise.
    """
    # Normalize: keep only alphanumeric characters and convert to lower case
    cleaned = ''.join(ch.lower() for ch in s if ch.isalnum())
    return cleaned == cleaned[::-1]
```

Feedback:

```
all tests passed
```


## rle (tricky): passed, best 8/8 tests

### Attempt 1: passed (8/8 tests, 2.9s)

File `solution.py`:

```python
def compress(s: str) -> str:
    """
    Compress a string using run-length encoding with the following rules:
    - Each run of the same character is written as <count><char>.
    - The count is omitted when it is 1.
    - Runs longer than 9 are split into chunks of at most 9.
      For example, 'a'*12 becomes '9a3a' and 'a'*10 becomes '9aa'.

    Parameters
    ----------
    s : str
        The input string to compress.

    Returns
    -------
    str
        The compressed representation of the input string.
    """
    if not s:
        return ""

    result_parts = []
    current_char = s[0]
    count = 1

    for ch in s[1:]:
        if ch == current_char:
            count += 1
        else:
            # Flush the current run
            while count > 9:
                result_parts.append("9" + current_char)
                count -= 9
            if count == 1:
                result_parts.append(current_char)
            else:
                result_parts.append(str(count) + current_char)
            # Start new run
            current_char = ch
            count = 1

    # Flush the final run
    while count > 9:
        result_parts.append("9" + current_char)
        count -= 9
    if count == 1:
        result_parts.append(current_char)
    else:
        result_parts.append(str(count) + current_char)

    return "".join(result_parts)
```

Feedback:

```
all tests passed
```


## roman (easy): passed, best 5/5 tests

### Attempt 1: passed (5/5 tests, 1.6s)

File `solution.py`:

```python
"""
Roman numeral to integer conversion.

This module provides a single function `roman_to_int` that converts a Roman numeral
string into its integer representation. The implementation follows the standard
rules for Roman numerals, including subtractive notation (e.g., IV = 4, IX = 9,
XL = 40, XC = 90, CD = 400, CM = 900).

The function is tolerant of an empty string, returning 0 in that case. It
expects the input to be a string containing only the characters I, V, X, L,
C, D, and M in uppercase. No validation of malformed numerals is performed
beyond the basic conversion logic.

Example:
    >>> roman_to_int('MCMXCIV')
    1994
"""

from __future__ import annotations

__all__ = ["roman_to_int"]


def roman_to_int(s: str) -> int:
    """
    Convert a Roman numeral string to an integer.

    Parameters
    ----------
    s : str
        Roman numeral string (e.g., 'MCMXCIV').

    Returns
    -------
    int
        The integer value of the Roman numeral.

    Notes
    -----
    The function handles the standard Roman numeral symbols:
        I  -> 1
        V  -> 5
        X  -> 10
        L  -> 50
        C  -> 100
        D  -> 500
        M  -> 1000

    Subtractive pairs are recognized:
        IV -> 4, IX -> 9, XL -> 40, XC -> 90, CD -> 400, CM -> 900

    An empty string returns 0. The function does not perform extensive
    validation of malformed numerals; it simply applies the conversion
    algorithm.
    """
    if not s:
        return 0

    # Mapping of single Roman numerals to their integer values.
    roman_map = {
        "I": 1,
        "V": 5,
        "X": 10,
        "L": 50,
        "C": 100,
        "D": 500,
        "M": 1000,
    }

    total = 0
    i = 0
    n = len(s)

    while i < n:
        # Current numeral value
        curr_val = roman_map.get(s[i], 0)

        # Look ahead to the next numeral if it exists
        if i + 1 < n:
            next_val = roman_map.get(s[i + 1], 0)
            if curr_val < next_val:
                # Subtractive pair detected
                total += next_val - curr_val
                i += 2
                continue

        # Regular addition
        total += curr_val
        i += 1

    return total
```

Feedback:

```
all tests passed
```


## spiral (tricky): passed, best 5/5 tests

### Attempt 1: passed (5/5 tests, 17.2s)

File `solution.py`:

```python
"""
Solution for generating an n x n matrix filled with numbers 1..n*n
in a counter-clockwise spiral order starting from the top-left corner
and moving down first.
"""

from __future__ import annotations
from typing import List


def spiral_ccw(n: int) -> List[List[int]]:
    """
    Return an n x n matrix filled with integers from 1 to n*n in a
    counter-clockwise spiral order. The spiral starts at the top-left
    corner, moves down first, then right, up, left, and continues
    inward.

    Parameters
    ----------
    n : int
        Size of the matrix. If n is 0, an empty list is returned.

    Returns
    -------
    List[List[int]]
        The resulting n x n matrix.

    Examples
    --------
    >>> spiral_ccw(0)
    []
    >>> spiral_ccw(1)
    [[1]]
    >>> spiral_ccw(2)
    [[1, 4], [2, 3]]
    >>> spiral_ccw(3)
    [[1, 8, 7], [2, 9, 6], [3, 4, 5]]
    """
    if n <= 0:
        return []

    # Initialize an n x n matrix with zeros
    matrix: List[List[int]] = [[0] * n for _ in range(n)]

    # Boundaries of the current layer
    top, bottom = 0, n - 1
    left, right = 0, n - 1

    current = 1  # Next number to place

    while current <= n * n:
        # 1. Move down along the leftmost column
        for i in range(top, bottom + 1):
            if current > n * n:
                break
            matrix[i][left] = current
            current += 1
        left += 1  # The left column has been filled

        # 2. Move right along the bottom row
        for j in range(left, right + 1):
            if current > n * n:
                break
            matrix[bottom][j] = current
            current += 1
        bottom -= 1  # The bottom row has been filled

        # 3. Move up along the rightmost column
        for i in range(bottom, top - 1, -1):
            if current > n * n:
                break
            matrix[i][right] = current
            current += 1
        right -= 1  # The right column has been filled

        # 4. Move left along the top row
        for j in range(right, left - 1, -1):
            if current > n * n:
                break
            matrix[top][j] = current
            current += 1
        top += 1  # The top row has been filled

    return matrix
```

Feedback:

```
all tests passed
```


## version (tricky): passed, best 9/9 tests

### Attempt 1: passed (9/9 tests, 1.5s)

File `solution.py`:

```python
"""
Solution for comparing version strings.

The compare_versions function implements the following rules:

1. Versions are dot-separated numbers compared as integers.
   Example: '1.10' > '1.9'.

2. Missing parts are treated as 0.
   Example: '1.0' == '1'.

3. A version may end with '-<label>' (pre-release). A labeled version is
   considered lower than the same version without a label.
   Example: '1.0-beta' < '1.0'.

4. When both versions have labels, they are compared alphabetically.
   Example: '1.0-alpha' < '1.0-beta'.

5. Numbers are compared before labels.

The function returns:
- -1 if a < b
-  0 if a == b
-  1 if a > b
"""

from __future__ import annotations


def _parse_version(v: str) -> tuple[list[int], str | None]:
    """
    Parse a version string into a list of integer parts and an optional label.

    Parameters
    ----------
    v : str
        The version string to parse.

    Returns
    -------
    tuple[list[int], str | None]
        A tuple containing the list of integer parts and the label (or None).
    """
    if "-" in v:
        base, label = v.split("-", 1)
    else:
        base, label = v, None

    # Convert each numeric part to int; empty parts are treated as 0
    parts = [int(part) if part else 0 for part in base.split(".")]
    return parts, label


def compare_versions(a: str, b: str) -> int:
    """
    Compare two version strings according to the rules described in the module docstring.

    Parameters
    ----------
    a : str
        First version string.
    b : str
        Second version string.

    Returns
    -------
    int
        -1 if a < b, 0 if a == b, 1 if a > b.
    """
    parts_a, label_a = _parse_version(a)
    parts_b, label_b = _parse_version(b)

    # Compare numeric parts
    max_len = max(len(parts_a), len(parts_b))
    for i in range(max_len):
        val_a = parts_a[i] if i < len(parts_a) else 0
        val_b = parts_b[i] if i < len(parts_b) else 0
        if val_a < val_b:
            return -1
        if val_a > val_b:
            return 1

    # Numeric parts are equal; compare labels
    if label_a is None and label_b is None:
        return 0
    if label_a is None:
        # a has no label, b does -> a > b
        return 1
    if label_b is None:
        # b has no label, a does -> a < b
        return -1

    # Both have labels; compare alphabetically
    if label_a < label_b:
        return -1
    if label_a > label_b:
        return 1
    return 0
```

Feedback:

```
all tests passed
```


## weekday (tricky): passed, best 10/10 tests

### Attempt 1: passed (10/10 tests, 1.9s)

File `solution.py`:

```python
"""
Solution for nth_weekday problem.

The function nth_weekday returns the day of the month for the nth occurrence
of a given weekday in a specified month and year. Positive n counts from the
beginning of the month, negative n counts from the end. n=0 or a non-existent
occurrence raises ValueError.
"""

import calendar
from typing import Final

__all__: Final = ["nth_weekday"]


def nth_weekday(year: int, month: int, weekday: int, n: int) -> int:
    """
    Return the day of the month for the nth occurrence of a weekday.

    Parameters
    ----------
    year : int
        The year (e.g., 2023).
    month : int
        The month (1-12).
    weekday : int
        The weekday (0=Monday, 6=Sunday).
    n : int
        The occurrence number. Positive values count from the start of the
        month, negative values count from the end. n=0 is invalid.

    Returns
    -------
    int
        The day of the month (1-31) corresponding to the nth occurrence.

    Raises
    ------
    ValueError
        If n is 0 or the requested occurrence does not exist in the month.
    """
    if n == 0:
        raise ValueError("n must not be zero")

    # Validate weekday range
    if not 0 <= weekday <= 6:
        raise ValueError("weekday must be in 0..6")

    # Get first weekday of the month and number of days in month
    first_weekday, month_days = calendar.monthrange(year, month)

    if n > 0:
        # Day of the first occurrence of the desired weekday
        first_occurrence_day = 1 + (weekday - first_weekday) % 7
        # Compute nth occurrence
        day = first_occurrence_day + (n - 1) * 7
        if day > month_days:
            raise ValueError("The requested occurrence does not exist")
        return day
    else:
        # Compute last weekday of the month
        last_weekday_of_month = (first_weekday + month_days - 1) % 7
        # Day of the last occurrence of the desired weekday
        last_occurrence_day = month_days - (last_weekday_of_month - weekday) % 7
        # Compute nth from the end
        day = last_occurrence_day + (n + 1) * 7
        if day < 1:
            raise ValueError("The requested occurrence does not exist")
        return day
```

Feedback:

```
all tests passed
```


## wrap (tricky): passed, best 7/7 tests

### Attempt 1: passed (7/7 tests, 33.8s)

File `solution.py`:

```python
def wrap_text(text: str, width: int) -> list[str]:
    """
    Split ``text`` into words on any whitespace and pack them greedily into lines
    of at most ``width`` characters. Words are joined by a single space. If a
    word is longer than ``width``, it is split into pieces of exactly ``width``
    characters, each piece on its own line, except the last piece which starts
    a new line that may receive subsequent words.

    Parameters
    ----------
    text : str
        The input string to wrap.
    width : int
        The maximum number of characters per line. Must be a positive integer.

    Returns
    -------
    list[str]
        A list of wrapped lines. An empty list is returned for empty or
        whitespace-only input.

    Examples
    --------
    >>> wrap_text("Hello world", 10)
    ['Hello', 'world']

    >>> wrap_text("Supercalifragilisticexpialidocious", 10)
    ['Supercalif', 'ragilistic', 'expialidoc', 'ious']

    >>> wrap_text("  ", 5)
    []
    """
    if not text or text.strip() == "":
        return []

    if width <= 0:
        raise ValueError("width must be a positive integer")

    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        # Handle normal words
        if len(word) <= width:
            if not current_line:
                current_line = word
            else:
                # Check if adding the word would exceed width
                if len(current_line) + 1 + len(word) <= width:
                    current_line += " " + word
                else:
                    lines.append(current_line)
                    current_line = word
        else:
            # Word longer than width: split into pieces
            # Flush any existing line
            if current_line:
                lines.append(current_line)
                current_line = ""

            # Split the word into chunks of size width
            for i in range(0, len(word), width):
                piece = word[i : i + width]
                # All pieces except the last are full-width lines
                if i + width < len(word):
                    lines.append(piece)
                else:
                    # Last piece starts a new line that may receive more words
                    current_line = piece

    # Append any remaining line
    if current_line:
        lines.append(current_line)

    return lines
```

Feedback:

```
all tests passed
```

