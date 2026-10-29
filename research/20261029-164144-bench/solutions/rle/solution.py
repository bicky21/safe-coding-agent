def compress(s: str) -> str:
    """
    Compress a string using run-length encoding with the following rules:
    - Each run of the same character is written as <count><char>.
    - The count is omitted when it is 1.
    - Runs longer than 9 are split into chunks of at most 9.
      For example, 'a'*12 becomes '9a3a' and 'a'*10 becomes '9aa'.

    Parameters
    ----------
    s : str
        The input string to compress.

    Returns
    -------
    str
        The compressed representation of the input string.
    """
    if not s:
        return ""

    result_parts = []
    current_char = s[0]
    count = 1

    for ch in s[1:]:
        if ch == current_char:
            count += 1
        else:
            # Flush the current run
            while count > 9:
                result_parts.append("9" + current_char)
                count -= 9
            if count == 1:
                result_parts.append(current_char)
            else:
                result_parts.append(str(count) + current_char)
            # Start new run
            current_char = ch
            count = 1

    # Flush the final run
    while count > 9:
        result_parts.append("9" + current_char)
        count -= 9
    if count == 1:
        result_parts.append(current_char)
    else:
        result_parts.append(str(count) + current_char)

    return "".join(result_parts)