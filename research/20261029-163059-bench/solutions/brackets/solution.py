def is_balanced(s: str) -> bool:
    """
    Returns True if every bracket ( ) [ ] { } in s is correctly opened and closed.
    Ignores other characters.
    """
    stack = []
    matching = {')': '(', ']': '[', '}': '{'}
    opening = set(matching.values())
    
    for char in s:
        if char in opening:
            stack.append(char)
        elif char in matching:
            if not stack or stack[-1] != matching[char]:
                return False
            stack.pop()
    
    return len(stack) == 0