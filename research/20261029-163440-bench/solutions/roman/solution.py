def roman_to_int(s: str) -> int:
    """
    Convert a Roman numeral string to an integer.
    
    Args:
        s: A string representing a Roman numeral (e.g., 'MCMXCIV')
        
    Returns:
        The integer value of the Roman numeral
    """
    roman_values = {
        'I': 1,
        'V': 5,
        'X': 10,
        'L': 50,
        'C': 100,
        'D': 500,
        'M': 1000
    }
    
    total = 0
    prev_value = 0
    
    # Iterate through the string in reverse
    for char in reversed(s):
        value = roman_values[char]
        
        # If the current value is less than the previous value,
        # it means we have a subtractive notation (e.g., IV = 4)
        if value < prev_value:
            total -= value
        else:
            total += value
        
        prev_value = value
    
    return total