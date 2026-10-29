def spiral_ccw(n: int) -> list[list[int]]:
    if n <= 0:
        return []
    
    matrix = [[0] * n for _ in range(n)]
    
    # Boundaries
    top, bottom = 0, n - 1
    left, right = 0, n - 1
    
    num = 1
    total = n * n
    
    while num <= total:
        # Go DOWN along the left column
        for i in range(top, bottom + 1):
            matrix[i][left] = num
            num += 1
        left += 1
        
        if num > total:
            break
        
        # Go RIGHT along the bottom row
        for j in range(left, right + 1):
            matrix[bottom][j] = num
            num += 1
        bottom -= 1
        
        if num > total:
            break
        
        # Go UP along the right column
        for i in range(bottom, top - 1, -1):
            matrix[i][right] = num
            num += 1
        right -= 1
        
        if num > total:
            break
        
        # Go LEFT along the top row
        for j in range(right, left - 1, -1):
            matrix[top][j] = num
            num += 1
        top += 1
    
    return matrix