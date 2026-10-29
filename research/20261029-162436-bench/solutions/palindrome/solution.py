def is_palindrome(s: str) -> bool:
    """
    Return True if the given string `s` is a palindrome, ignoring case,
    spaces, and punctuation. Non-alphanumeric characters are removed
    before the palindrome check.

    Parameters
    ----------
    s : str
        The string to check.

    Returns
    -------
    bool
        True if `s` is a palindrome under the described conditions,
        False otherwise.
    """
    # Keep only alphanumeric characters and convert to lowercase
    cleaned = ''.join(ch.lower() for ch in s if ch.isalnum())
    # A string is a palindrome if it reads the same forwards and backwards
    return cleaned == cleaned[::-1]