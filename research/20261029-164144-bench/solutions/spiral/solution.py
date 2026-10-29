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