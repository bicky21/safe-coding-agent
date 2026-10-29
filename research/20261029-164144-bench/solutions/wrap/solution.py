def wrap_text(text: str, width: int) -> list[str]:
    """
    Split ``text`` into words on any whitespace and pack them greedily into lines
    of at most ``width`` characters. Words are joined by a single space. If a
    word is longer than ``width``, it is split into pieces of exactly ``width``
    characters, each piece on its own line, except the last piece which starts
    a new line that may receive subsequent words.

    Parameters
    ----------
    text : str
        The input string to wrap.
    width : int
        The maximum number of characters per line. Must be a positive integer.

    Returns
    -------
    list[str]
        A list of wrapped lines. An empty list is returned for empty or
        whitespace-only input.

    Examples
    --------
    >>> wrap_text("Hello world", 10)
    ['Hello', 'world']

    >>> wrap_text("Supercalifragilisticexpialidocious", 10)
    ['Supercalif', 'ragilistic', 'expialidoc', 'ious']

    >>> wrap_text("  ", 5)
    []
    """
    if not text or text.strip() == "":
        return []

    if width <= 0:
        raise ValueError("width must be a positive integer")

    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        # Handle normal words
        if len(word) <= width:
            if not current_line:
                current_line = word
            else:
                # Check if adding the word would exceed width
                if len(current_line) + 1 + len(word) <= width:
                    current_line += " " + word
                else:
                    lines.append(current_line)
                    current_line = word
        else:
            # Word longer than width: split into pieces
            # Flush any existing line
            if current_line:
                lines.append(current_line)
                current_line = ""

            # Split the word into chunks of size width
            for i in range(0, len(word), width):
                piece = word[i : i + width]
                # All pieces except the last are full-width lines
                if i + width < len(word):
                    lines.append(piece)
                else:
                    # Last piece starts a new line that may receive more words
                    current_line = piece

    # Append any remaining line
    if current_line:
        lines.append(current_line)

    return lines