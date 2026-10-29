def is_palindrome(s: str) -> bool:
    """
    Returns True if s is a palindrome, ignoring case, spaces and punctuation.
    """
    cleaned = [ch.lower() for ch in s if ch.isalnum()]
    return cleaned == cleaned[::-1]