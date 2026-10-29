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