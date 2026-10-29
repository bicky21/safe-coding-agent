# Run log

Settings: {"model": "openai:openai/gpt-oss-20b", "max_attempts": 1, "feedback": "detailed", "anti_stuck": true, "plan_first": false, "safety": "task default"}

Runner: local

## brackets (medium): passed, best 6/6 tests

### Attempt 1: passed (6/6 tests, 1.4s)

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
    # Mapping of closing to opening brackets for quick lookup
    bracket_pairs = {')': '(', ']': '[', '}': '{'}
    opening_brackets = set(bracket_pairs.values())

    stack = []

    for char in s:
        if char in opening_brackets:
            stack.append(char)
        elif char in bracket_pairs:
            if not stack or stack[-1] != bracket_pairs[char]:
                return False
            stack.pop()

    # If stack is empty, all opening brackets were matched
    return not stack
```

Feedback:

```
all tests passed
```


## dijkstra (hard): passed, best 4/4 tests

### Attempt 1: passed (4/4 tests, 1.6s)

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
        non-negative integers.
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

    # Min-heap priority queue: (current_distance, node)
    heap = [(0.0, src)]

    while heap:
        d_u, u = heapq.heappop(heap)

        # If we have already found a better path to u, skip
        if d_u > dist[u]:
            continue

        for v, w in adj[u]:
            new_dist = d_u + w
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

### Attempt 1: passed (12/12 tests, 4.0s)

File `solution.py`:

```python
"""
Utility module for parsing duration strings into seconds.

The main function `parse_duration` accepts a string representation of a duration
(e.g. "1h30m", "2d 3h", "45s") and returns the total number of seconds as an
integer. The string may contain the units days (d), hours (h), minutes (m),
and seconds (s) in that order, each appearing at most once. Spaces between
components are allowed. Any deviation from the expected format raises a
ValueError.
"""

import re
from typing import Dict

__all__ = ["parse_duration"]


def parse_duration(s: str) -> int:
    """
    Convert a duration string into total seconds.

    Parameters
    ----------
    s : str
        Duration string containing optional whitespace and units in the
        order d, h, m, s. Units are case-insensitive. Each unit may appear
        at most once.

    Returns
    -------
    int
        Total number of seconds represented by the duration.

    Raises
    ------
    ValueError
        If the input string is empty, contains invalid characters,
        has units out of order, repeats a unit, or has a number without a
        unit (or vice versa).
    """
    if not isinstance(s, str):
        raise ValueError("Input must be a string")

    # Remove all whitespace for easier processing
    cleaned = "".join(s.split())
    if not cleaned:
        raise ValueError("Empty duration string")

    # Regular expression to capture a number followed by a unit
    pattern = re.compile(r"(?i)(\d+)([dhms])")
    matches = list(pattern.finditer(cleaned))

    if not matches:
        raise ValueError("No valid duration components found")

    # Ensure that the entire cleaned string is consumed by the matches
    concatenated = "".join(m.group(0) for m in matches)
    if concatenated != cleaned:
        raise ValueError("Invalid format or unknown characters in duration")

    # Order enforcement: d -> h -> m -> s
    order = {"d": 0, "h": 1, "m": 2, "s": 3}
    seen_units = set()
    last_index = -1

    total_seconds = 0
    unit_to_seconds: Dict[str, int] = {"d": 86400, "h": 3600, "m": 60, "s": 1}

    for match in matches:
        number_str, unit = match.group(1), match.group(2).lower()

        # Check for repeated units
        if unit in seen_units:
            raise ValueError(f"Repeated unit '{unit}' in duration")
        seen_units.add(unit)

        # Enforce order
        current_index = order[unit]
        if current_index <= last_index:
            raise ValueError(f"Unit '{unit}' out of order in duration")
        last_index = current_index

        # Convert number to integer and validate
        try:
            value = int(number_str)
        except ValueError:
            raise ValueError(f"Invalid number '{number_str}' in duration")

        if value < 0:
            raise ValueError(f"Negative value '{value}' not allowed in duration")

        total_seconds += value * unit_to_seconds[unit]

    return total_seconds
```

Feedback:

```
all tests passed
```


## intervals (medium): passed, best 5/5 tests

### Attempt 1: passed (5/5 tests, 1.2s)

File `solution.py`:

```python
from __future__ import annotations
from typing import List

def merge_intervals(intervals: List[List[int]]) -> List[List[int]]:
    """
    Merge all overlapping or touching intervals.

    Parameters
    ----------
    intervals : List[List[int]]
        A list of intervals, each represented as a two-element list [start, end].
        Intervals may be unsorted and may overlap or touch.

    Returns
    -------
    List[List[int]]
        A new list of merged intervals sorted by start value.
        Intervals that only touch (e.g., [1, 2] and [2, 3]) are merged into a single interval.
    """
    if not intervals:
        return []

    # Sort intervals by start value
    sorted_intervals = sorted(intervals, key=lambda x: x[0])

    merged: List[List[int]] = []
    current_start, current_end = sorted_intervals[0]

    for start, end in sorted_intervals[1:]:
        # If the current interval overlaps or touches the next one, merge them
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            merged.append([current_start, current_end])
            current_start, current_end = start, end

    # Append the last interval
    merged.append([current_start, current_end])

    return merged
```

Feedback:

```
all tests passed
```


## lcs (medium): passed, best 4/4 tests

### Attempt 1: passed (4/4 tests, 1.6s)

File `solution.py`:

```python
"""
Longest Common Subsequence implementation using dynamic programming.

The function `lcs(a: str, b: str) -> str` returns one longest common subsequence
of the two input strings `a` and `b`. If there are multiple LCSs of the same
maximum length, any one of them is returned.

The algorithm builds a 2D table `dp` where `dp[i][j]` stores the length of the
LCS of `a[:i]` and `b[:j]`. After filling the table, it reconstructs an LCS
by walking backwards from `dp[len(a)][len(b)]` to the start.
"""

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
    # Edge cases: if either string is empty, return empty string
    if not a or not b:
        return ""

    n, m = len(a), len(b)

    # dp[i][j] will hold the length of LCS of a[:i] and b[:j]
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    # Fill dp table
    for i in range(1, n + 1):
        ai = a[i - 1]
        for j in range(1, m + 1):
            if ai == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # Reconstruct one LCS by walking backwards
    i, j = n, m
    lcs_chars = []

    while i > 0 and j > 0:
        if a[i - 1] == b[j - 1]:
            # Character is part of LCS
            lcs_chars.append(a[i - 1])
            i -= 1
            j -= 1
        else:
            # Move in the direction of the larger dp value
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

### Attempt 1: passed (7/7 tests, 1.4s)

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

### Attempt 1: passed (4/4 tests, 4.0s)

File `solution.py`:

```python
def is_palindrome(s: str) -> bool:
    """
    Return True if the given string `s` is a palindrome, ignoring case,
    spaces, and punctuation. Non-alphanumeric characters are removed
    before the palindrome check.

    Parameters
    ----------
    s : str
        The string to check.

    Returns
    -------
    bool
        True if `s` is a palindrome under the described conditions,
        False otherwise.
    """
    # Keep only alphanumeric characters and convert to lowercase
    cleaned = ''.join(ch.lower() for ch in s if ch.isalnum())
    # A string is a palindrome if it reads the same forwards and backwards
    return cleaned == cleaned[::-1]
```

Feedback:

```
all tests passed
```


## rle (tricky): passed, best 8/8 tests

### Attempt 1: passed (8/8 tests, 5.4s)

File `solution.py`:

```python
def compress(s: str) -> str:
    """
    Run-length encode the input string `s` according to the following rules:
    - Each run of the same character is written as <count><char>.
    - The count is omitted when it is 1.
    - Runs longer than 9 are split into chunks of at most 9 characters.
      For example, 'a'*12 becomes '9a3a' and 'a'*10 becomes '9aa'.

    Parameters
    ----------
    s : str
        The string to compress.

    Returns
    -------
    str
        The run-length encoded representation of `s`.
    """
    if not s:
        return ""

    result_parts = []
    i = 0
    n = len(s)

    while i < n:
        current_char = s[i]
        count = 1
        i += 1
        while i < n and s[i] == current_char:
            count += 1
            i += 1

        # Split runs longer than 9 into chunks of at most 9
        while count > 0:
            chunk = min(count, 9)
            if chunk == 1:
                result_parts.append(current_char)
            else:
                result_parts.append(f"{chunk}{current_char}")
            count -= chunk

    return "".join(result_parts)
```

Feedback:

```
all tests passed
```


## roman (easy): passed, best 5/5 tests

### Attempt 1: passed (5/5 tests, 1.7s)

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
C, D, and M in uppercase. If the input contains any other characters, a
`ValueError` is raised.

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

    Raises
    ------
    ValueError
        If the input string contains characters other than the standard Roman
        numeral symbols (I, V, X, L, C, D, M).

    Notes
    -----
    The function implements the classic subtractive notation:
        - IV = 4
        - IX = 9
        - XL = 40
        - XC = 90
        - CD = 400
        - CM = 900

    An empty string is considered to represent the value 0.
    """
    if not s:
        return 0

    # Mapping of single Roman numeral characters to their integer values.
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
    prev_value = 0

    # Process the string from right to left to simplify subtractive logic.
    for char in reversed(s):
        if char not in roman_map:
            raise ValueError(f"Invalid Roman numeral character: {char!r}")

        value = roman_map[char]
        if value < prev_value:
            # Subtractive case: subtract this value.
            total -= value
        else:
            # Additive case: add this value.
            total += value
            prev_value = value

    return total
```

Feedback:

```
all tests passed
```


## spiral (tricky): passed, best 5/5 tests

### Attempt 1: passed (5/5 tests, 3.5s)

File `solution.py`:

```python
"""
Solution for generating an n x n matrix filled with numbers 1..n*n
in a counter-clockwise spiral order, starting at the top-left corner
and moving down first.

Author: ChatGPT
"""

def spiral_ccw(n: int) -> list[list[int]]:
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
    list[list[int]]
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
    if n == 0:
        return []

    # Initialize an n x n matrix filled with zeros
    matrix = [[0] * n for _ in range(n)]

    # Directions: down, right, up, left
    dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    dir_idx = 0  # start with 'down'

    r, c = 0, 0  # starting position
    for val in range(1, n * n + 1):
        matrix[r][c] = val
        if val == n * n:
            break

        # Compute next position
        dr, dc = dirs[dir_idx]
        nr, nc = r + dr, c + dc

        # If next position is out of bounds or already filled,
        # change direction clockwise (counter-clockwise spiral)
        if nr < 0 or nr >= n or nc < 0 or nc >= n or matrix[nr][nc] != 0:
            dir_idx = (dir_idx + 1) % 4
            dr, dc = dirs[dir_idx]
            nr, nc = r + dr, c + dc

        r, c = nr, nc

    return matrix
```

Feedback:

```
all tests passed
```


## version (tricky): passed, best 9/9 tests

### Attempt 1: passed (9/9 tests, 25.8s)

File `solution.py`:

```python
def compare_versions(a: str, b: str) -> int:
    """
    Compare two version strings.

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

    Rules
    -----
    * Versions are dot-separated numbers compared as integers.
      Example: '1.10' > '1.9'.
    * Missing parts count as 0.
      Example: '1.0' == '1'.
    * A version may end with '-<label>' (pre‑release), which makes it
      lower than the same version without a label.
      Example: '1.0-beta' < '1.0'.
    * Two labels are compared alphabetically.
      Example: '1.0-alpha' < '1.0-beta'.
    * Numbers are compared before labels.
    """
    def _split_version(v: str):
        """Return (numeric_parts, label) where numeric_parts is a list of ints."""
        if '-' in v:
            base, label = v.split('-', 1)
        else:
            base, label = v, None
        # Convert numeric parts to ints; ignore empty parts (shouldn't happen)
        parts = [int(p) for p in base.split('.')]
        return parts, label

    parts_a, label_a = _split_version(a)
    parts_b, label_b = _split_version(b)

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

### Attempt 1: passed (10/10 tests, 7.1s)

File `solution.py`:

```python
"""
Solution for nth_weekday problem.

Provides a function `nth_weekday` that returns the day of the month for the
n-th occurrence of a given weekday in a specified month and year.

The function uses the `calendar` module to determine month lengths and
weekday positions. It validates inputs and raises `ValueError` for
invalid arguments or when the requested occurrence does not exist.
"""

import calendar
from typing import Final

# Constants for weekday indices
MONDAY: Final[int] = 0
TUESDAY: Final[int] = 1
WEDNESDAY: Final[int] = 2
THURSDAY: Final[int] = 3
FRIDAY: Final[int] = 4
SATURDAY: Final[int] = 5
SUNDAY: Final[int] = 6


def nth_weekday(year: int, month: int, weekday: int, n: int) -> int:
    """
    Return the day of the month for the n-th occurrence of a given weekday.

    Parameters
    ----------
    year : int
        The year (e.g., 2023).
    month : int
        The month (1-12).
    weekday : int
        The weekday index (0=Monday, 6=Sunday).
    n : int
        The occurrence number:
            * n > 0 : the n-th occurrence from the start of the month.
            * n < 0 : the |n|-th occurrence from the end of the month.
            * n == 0 : invalid, raises ValueError.

    Returns
    -------
    int
        The day of the month (1-31) corresponding to the requested
        occurrence.

    Raises
    ------
    ValueError
        If `n` is 0, if `weekday` is not in 0..6, or if the requested
        occurrence does not exist in the specified month.
    """
    # Validate weekday
    if not 0 <= weekday <= 6:
        raise ValueError(f"weekday must be in 0..6, got {weekday}")

    # Validate n
    if n == 0:
        raise ValueError("n must not be zero")

    # Get first weekday of the month and number of days in month
    first_weekday, month_days = calendar.monthrange(year, month)

    # Compute the first occurrence of the desired weekday
    offset_first = (weekday - first_weekday) % 7
    first_occurrence_day = 1 + offset_first

    if n > 0:
        # n-th occurrence from the start
        day = first_occurrence_day + (n - 1) * 7
        if day > month_days:
            raise ValueError(
                f"{n}-th occurrence of weekday {weekday} does not exist "
                f"in {year}-{month:02d}"
            )
        return day

    # n < 0: occurrence from the end
    # Compute the weekday of the last day of the month
    last_weekday = (first_weekday + month_days - 1) % 7
    offset_last = (last_weekday - weekday) % 7
    last_occurrence_day = month_days - offset_last

    day = last_occurrence_day + (n + 1) * 7  # n is negative
    if day < 1:
        raise ValueError(
            f"{n}-th occurrence of weekday {weekday} does not exist "
            f"in {year}-{month:02d}"
        )
    return day
```

Feedback:

```
all tests passed
```


## wrap (tricky): passed, best 7/7 tests

### Attempt 1: passed (7/7 tests, 9.9s)

File `solution.py`:

```python
"""
Solution for the wrap_text problem.

The function `wrap_text` splits a given text into words and packs them into lines
of at most a specified width. Long words are split into fixed-width pieces
according to the rules described in the task.
"""

from __future__ import annotations


def wrap_text(text: str, width: int) -> list[str]:
    """
    Split `text` into words and pack them greedily into lines of at most
    `width` characters. Words are joined by a single space. If a word is
    longer than `width`, it is split into pieces of exactly `width`
    characters, each piece on its own line, except the last piece which
    starts a new line that may receive additional words.

    Parameters
    ----------
    text : str
        The input text to wrap.
    width : int
        The maximum width of each line.

    Returns
    -------
    list[str]
        A list of wrapped lines. An empty list is returned for empty or
        whitespace-only input.
    """
    # Return empty list for empty or whitespace-only input
    if not text or text.strip() == "":
        return []

    if width <= 0:
        raise ValueError("width must be a positive integer")

    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        # Handle words longer than width
        if len(word) > width:
            # Flush current line if it has content
            if current_line:
                lines.append(current_line)
                current_line = ""

            # Split the long word into width-sized pieces
            pieces = [word[i : i + width] for i in range(0, len(word), width)]
            # All pieces except the last are full-width lines
            for piece in pieces[:-1]:
                lines.append(piece)
            # The last piece starts a new line that may receive more words
            current_line = pieces[-1]
            continue

        # Normal word handling
        if not current_line:
            # Start a new line with the word
            current_line = word
        else:
            # Check if adding the word would exceed the width
            if len(current_line) + 1 + len(word) <= width:
                current_line += " " + word
            else:
                # Flush the current line and start a new one
                lines.append(current_line)
                current_line = word

    # Append any remaining content in the current line
    if current_line:
        lines.append(current_line)

    return lines
```

Feedback:

```
all tests passed
```

