def compress(s: str) -> str:
    if not s:
        return ""
    
    result = []
    i = 0
    n = len(s)
    
    while i < n:
        char = s[i]
        count = 0
        while i < n and s[i] == char:
            count += 1
            i += 1
        
        # Split the run into chunks of at most 9
        while count > 0:
            chunk = min(count, 9)
            if chunk == 1:
                result.append(char)
            else:
                result.append(str(chunk))
                result.append(char)
            count -= chunk
    
    return "".join(result)