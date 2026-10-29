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
]
