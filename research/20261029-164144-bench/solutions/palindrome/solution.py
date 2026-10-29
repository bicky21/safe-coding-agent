def is_palindrome(s: str) -> bool:
    """
    Return True if the input string s is a palindrome, ignoring case,
    spaces, and punctuation. Non-alphanumeric characters are removed
    before comparison.

    Parameters
    ----------
    s : str
        The string to check.

    Returns
    -------
    bool
        True if s is a palindrome under the described conditions, False otherwise.
    """
    # Normalize: keep only alphanumeric characters and convert to lower case
    cleaned = ''.join(ch.lower() for ch in s if ch.isalnum())
    return cleaned == cleaned[::-1]