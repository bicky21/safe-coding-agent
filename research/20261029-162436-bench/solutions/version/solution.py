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