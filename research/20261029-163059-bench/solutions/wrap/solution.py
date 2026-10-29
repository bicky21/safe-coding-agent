def wrap_text(text: str, width: int) -> list[str]:
    if width <= 0:
        return []
    
    # Split text on any whitespace into words
    words = text.split()
    
    if not words:
        return []
    
    lines = []
    current_line = ""
    
    for word in words:
        if len(word) > width:
            # First, if there's a current line, flush it
            if current_line:
                lines.append(current_line)
                current_line = ""
            
            # Cut the word into pieces of exactly width characters
            i = 0
            while i < len(word):
                piece = word[i:i + width]
                if i + width < len(word):
                    # This piece is exactly width characters and not the last
                    lines.append(piece)
                else:
                    # This is the last piece (shorter or equal to width)
                    # It starts a new line that later words may join
                    current_line = piece
                i += width
        else:
            # Word fits within width
            if not current_line:
                current_line = word
            else:
                # Check if adding this word would exceed width
                if len(current_line) + 1 + len(word) <= width:
                    current_line = current_line + " " + word
                else:
                    lines.append(current_line)
                    current_line = word
    
    # Don't forget the last line
    if current_line:
        lines.append(current_line)
    
    return lines