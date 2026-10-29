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