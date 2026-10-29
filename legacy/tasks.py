"""
Benchmark tasks for the agent.

Each task has:
  name  - short id, used with:  python agent.py --task <name>
  level - easy / medium / hard
  task  - what we ask the model to write
  tests - assert statements; if any fails, the agent must fix its code
"""

TASKS = [
    {
        "name": "palindrome",
        "level": "easy",
        "task": (
            "Write a function is_palindrome(s: str) -> bool that returns True if s is a "
            "palindrome, ignoring case, spaces and punctuation."
        ),
        "tests": """
assert is_palindrome("A man, a plan, a canal: Panama") is True
assert is_palindrome("racecar") is True
assert is_palindrome("hello") is False
assert is_palindrome("") is True
""",
    },
    {
        "name": "roman",
        "level": "easy",
        "task": (
            "Write a function roman_to_int(s: str) -> int that converts a Roman numeral "
            "like 'MCMXCIV' to an integer."
        ),
        "tests": """
assert roman_to_int("III") == 3
assert roman_to_int("IV") == 4
assert roman_to_int("IX") == 9
assert roman_to_int("LVIII") == 58
assert roman_to_int("MCMXCIV") == 1994
""",
    },
    {
        "name": "brackets",
        "level": "medium",
        "task": (
            "Write a function is_balanced(s: str) -> bool that returns True if every "
            "bracket ( ) [ ] { } in s is correctly opened and closed. Ignore other characters."
        ),
        "tests": """
assert is_balanced("") is True
assert is_balanced("a(b)c[d]{e}") is True
assert is_balanced("([{}])") is True
assert is_balanced("([)]") is False
assert is_balanced("((") is False
assert is_balanced("}") is False
""",
    },
    {
        "name": "lcs",
        "level": "medium",
        "task": (
            "Write a function lcs(a: str, b: str) -> str that returns one longest common "
            "subsequence of a and b using dynamic programming."
        ),
        "tests": """
def _is_subseq(x, y):
    it = iter(y)
    return all(c in it for c in x)
for a, b, n in [("ABCBDAB", "BDCABA", 4), ("AGGTAB", "GXTXAYB", 4), ("", "ABC", 0), ("ABC", "DEF", 0)]:
    r = lcs(a, b)
    assert len(r) == n, (a, b, r)
    assert _is_subseq(r, a) and _is_subseq(r, b), (a, b, r)
""",
    },
    {
        "name": "intervals",
        "level": "medium",
        "task": (
            "Write a function merge_intervals(intervals: list[list[int]]) -> list[list[int]] "
            "that merges all overlapping intervals and returns them sorted by start. "
            "Intervals that only touch, like [1,2] and [2,3], also merge."
        ),
        "tests": """
assert merge_intervals([]) == []
assert merge_intervals([[1,3],[2,6],[8,10],[15,18]]) == [[1,6],[8,10],[15,18]]
assert merge_intervals([[1,4],[4,5]]) == [[1,5]]
assert merge_intervals([[5,7],[1,2],[2,3]]) == [[1,3],[5,7]]
assert merge_intervals([[1,10],[2,3],[4,5]]) == [[1,10]]
""",
    },
    {
        "name": "dijkstra",
        "level": "hard",
        "task": (
            "Write a function shortest_paths(n: int, edges: list[tuple[int, int, int]], "
            "src: int) -> list[float] for a directed graph with n nodes (0..n-1) and edges "
            "(u, v, weight >= 0). Return the shortest distance from src to every node, "
            "using float('inf') for unreachable nodes. Use Dijkstra's algorithm with heapq."
        ),
        "tests": """
INF = float('inf')
assert shortest_paths(1, [], 0) == [0]
assert shortest_paths(3, [(0,1,5)], 0) == [0, 5, INF]
assert shortest_paths(4, [(0,1,4),(0,2,1),(2,1,2),(1,3,1),(2,3,5)], 0) == [0, 3, 1, 4]
assert shortest_paths(3, [(0,1,1),(1,0,1),(1,2,0)], 2) == [INF, INF, 0]
""",
    },
    {
        "name": "lru",
        "level": "hard",
        "task": (
            "Write a class LRUCache with __init__(self, capacity: int), get(self, key: int) -> int "
            "(return -1 if missing) and put(self, key: int, value: int). When full, put must "
            "remove the least recently used key. Both get and put count as 'use'."
        ),
        "tests": """
c = LRUCache(2)
c.put(1, 1); c.put(2, 2)
assert c.get(1) == 1
c.put(3, 3)            # removes key 2
assert c.get(2) == -1
c.put(4, 4)            # removes key 1
assert c.get(1) == -1
assert c.get(3) == 3
assert c.get(4) == 4
c.put(3, 30)           # update counts as use
c.put(5, 5)            # removes key 4
assert c.get(4) == -1
assert c.get(3) == 30
""",
    },
    # ------------------------------------------------------------------
    # "tricky" tasks: unusual rules the model has NOT seen thousands of
    # times in training, so it cannot just recall a famous answer.
    # ------------------------------------------------------------------
    {
        "name": "rle",
        "level": "tricky",
        "task": (
            "Write a function compress(s: str) -> str using run-length encoding with these "
            "exact rules: each run of the same character is written as <count><char>; the "
            "count is left out when it is 1; a run longer than 9 is split into chunks of at "
            "most 9 (so 'a'*12 becomes '9a3a' and 'a'*10 becomes '9aa')."
        ),
        "tests": """
assert compress("") == ""
assert compress("abc") == "abc"
assert compress("aaabcc") == "3ab2c"
assert compress("aabbbaa") == "2a3b2a"
assert compress("a" * 9) == "9a"
assert compress("a" * 10) == "9aa"
assert compress("a" * 12) == "9a3a"
assert compress("x" * 19 + "y") == "9x9xxy"
""",
    },
    {
        "name": "duration",
        "level": "tricky",
        "task": (
            "Write a function parse_duration(s: str) -> int that converts a duration like "
            "'1h30m' into total seconds. Units are d, h, m, s (case-insensitive). Each unit "
            "may appear at most once and only in the order d, h, m, s. Spaces between parts "
            "are allowed. Raise ValueError for anything invalid, including an empty string, "
            "a number without a unit, a unit without a number, wrong order, or repeated units."
        ),
        "tests": """
assert parse_duration("1h30m") == 5400
assert parse_duration("2d") == 172800
assert parse_duration("1D 2H 3M 4S") == 93784
assert parse_duration("45s") == 45
assert parse_duration("0m") == 0
for bad in ["", "10", "h", "1x", "1m1h", "1h1h", "1h 30"]:
    try:
        parse_duration(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"expected ValueError for {bad!r}")
""",
    },
    {
        "name": "spiral",
        "level": "tricky",
        "task": (
            "Write a function spiral_ccw(n: int) -> list[list[int]] that returns an n x n "
            "matrix filled with 1..n*n in a COUNTER-clockwise spiral: start at the top-left "
            "corner, go DOWN first, then right, then up, then left, moving inward. "
            "spiral_ccw(0) returns []."
        ),
        "tests": """
assert spiral_ccw(0) == []
assert spiral_ccw(1) == [[1]]
assert spiral_ccw(2) == [[1, 4], [2, 3]]
assert spiral_ccw(3) == [[1, 8, 7], [2, 9, 6], [3, 4, 5]]
assert spiral_ccw(4) == [[1, 12, 11, 10], [2, 13, 16, 9], [3, 14, 15, 8], [4, 5, 6, 7]]
""",
    },
    {
        "name": "version",
        "level": "tricky",
        "task": (
            "Write a function compare_versions(a: str, b: str) -> int that returns -1 if a < b, "
            "0 if equal, 1 if a > b. Rules: versions are dot-separated numbers compared as "
            "integers ('1.10' > '1.9'); missing parts count as 0 ('1.0' == '1'); a version may "
            "end with '-<label>' (pre-release), which makes it LOWER than the same version "
            "without a label ('1.0-beta' < '1.0'); two labels are compared alphabetically "
            "('1.0-alpha' < '1.0-beta'). Numbers are compared before labels."
        ),
        "tests": """
assert compare_versions("1.0", "1") == 0
assert compare_versions("1.10", "1.9") == 1
assert compare_versions("1.2.3", "1.2.10") == -1
assert compare_versions("2", "1.99.99") == 1
assert compare_versions("1.0-beta", "1.0") == -1
assert compare_versions("1.0", "1.0-rc") == 1
assert compare_versions("1.0-alpha", "1.0-beta") == -1
assert compare_versions("1.0.0-beta", "1-beta") == 0
assert compare_versions("1.1-alpha", "1.0") == 1
""",
    },
    {
        "name": "wrap",
        "level": "tricky",
        "task": (
            "Write a function wrap_text(text: str, width: int) -> list[str] that splits text on "
            "any whitespace into words and packs them greedily into lines of at most width "
            "characters, with words joined by one space. A word longer than width is cut into "
            "pieces of exactly width characters, each piece on its own line, except the last "
            "(shorter or equal) piece, which starts a new line that later words may join. "
            "Empty or whitespace-only text returns []."
        ),
        "tests": """
assert wrap_text("", 5) == []
assert wrap_text("   ", 5) == []
assert wrap_text("the quick brown fox", 10) == ["the quick", "brown fox"]
assert wrap_text("a  b\\nc", 3) == ["a b", "c"]
assert wrap_text("abcdefghijkl xy", 5) == ["abcde", "fghij", "kl xy"]
assert wrap_text("supercalifragilistic is long", 8) == ["supercal", "ifragili", "stic is", "long"]
assert wrap_text("hi abcdef", 3) == ["hi", "abc", "def"]
""",
    },
    {
        "name": "weekday",
        "level": "tricky",
        "task": (
            "Write a function nth_weekday(year: int, month: int, weekday: int, n: int) -> int "
            "that returns the day of the month of the n-th given weekday (0=Monday ... "
            "6=Sunday). n=1 is the first, n=2 the second, n=-1 the last, n=-2 the second last. "
            "Raise ValueError if n is 0 or that occurrence does not exist. You may use the "
            "calendar or datetime modules."
        ),
        "tests": """
assert nth_weekday(2026, 10, 3, 1) == 1     # first Thursday of Oct 2026
assert nth_weekday(2026, 10, 3, 2) == 8
assert nth_weekday(2026, 10, 3, -1) == 29   # last Thursday
assert nth_weekday(2026, 10, 3, 5) == 29
assert nth_weekday(2024, 2, 3, -1) == 29    # leap year
assert nth_weekday(2026, 2, 0, 1) == 2
assert nth_weekday(2026, 2, 0, -1) == 23
for args in [(2026, 2, 0, 5), (2026, 10, 3, 0), (2026, 10, 3, -6)]:
    try:
        nth_weekday(*args)
    except ValueError:
        pass
    else:
        raise AssertionError(f"expected ValueError for {args}")
""",
    },
]
