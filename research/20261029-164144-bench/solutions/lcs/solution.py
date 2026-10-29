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