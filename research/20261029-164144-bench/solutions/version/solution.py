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