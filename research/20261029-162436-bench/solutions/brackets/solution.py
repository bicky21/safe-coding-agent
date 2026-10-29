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