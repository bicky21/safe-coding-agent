"""
Solution for the wrap_text problem.

The function `wrap_text` splits a given text into words and packs them into lines
of at most a specified width. Long words are split into fixed-width pieces
according to the rules described in the task.
"""

from __future__ import annotations


def wrap_text(text: str, width: int) -> list[str]:
    """
    Split `text` into words and pack them greedily into lines of at most
    `width` characters. Words are joined by a single space. If a word is
    longer than `width`, it is split into pieces of exactly `width`
    characters, each piece on its own line, except the last piece which
    starts a new line that may receive additional words.

    Parameters
    ----------
    text : str
        The input text to wrap.
    width : int
        The maximum width of each line.

    Returns
    -------
    list[str]
        A list of wrapped lines. An empty list is returned for empty or
        whitespace-only input.
    """
    # Return empty list for empty or whitespace-only input
    if not text or text.strip() == "":
        return []

    if width <= 0:
        raise ValueError("width must be a positive integer")

    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        # Handle words longer than width
        if len(word) > width:
            # Flush current line if it has content
            if current_line:
                lines.append(current_line)
                current_line = ""

            # Split the long word into width-sized pieces
            pieces = [word[i : i + width] for i in range(0, len(word), width)]
            # All pieces except the last are full-width lines
            for piece in pieces[:-1]:
                lines.append(piece)
            # The last piece starts a new line that may receive more words
            current_line = pieces[-1]
            continue

        # Normal word handling
        if not current_line:
            # Start a new line with the word
            current_line = word
        else:
            # Check if adding the word would exceed the width
            if len(current_line) + 1 + len(word) <= width:
                current_line += " " + word
            else:
                # Flush the current line and start a new one
                lines.append(current_line)
                current_line = word

    # Append any remaining content in the current line
    if current_line:
        lines.append(current_line)

    return lines