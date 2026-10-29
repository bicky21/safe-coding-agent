def compress(s: str) -> str:
    """
    Run-length encode the input string `s` according to the following rules:
    - Each run of the same character is written as <count><char>.
    - The count is omitted when it is 1.
    - Runs longer than 9 are split into chunks of at most 9 characters.
      For example, 'a'*12 becomes '9a3a' and 'a'*10 becomes '9aa'.

    Parameters
    ----------
    s : str
        The string to compress.

    Returns
    -------
    str
        The run-length encoded representation of `s`.
    """
    if not s:
        return ""

    result_parts = []
    i = 0
    n = len(s)

    while i < n:
        current_char = s[i]
        count = 1
        i += 1
        while i < n and s[i] == current_char:
            count += 1
            i += 1

        # Split runs longer than 9 into chunks of at most 9
        while count > 0:
            chunk = min(count, 9)
            if chunk == 1:
                result_parts.append(current_char)
            else:
                result_parts.append(f"{chunk}{current_char}")
            count -= chunk

    return "".join(result_parts)