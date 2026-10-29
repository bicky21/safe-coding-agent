import calendar


def nth_weekday(year: int, month: int, weekday: int, n: int) -> int:
    """
    Return the day of the month of the n-th given weekday.
    
    weekday: 0=Monday ... 6=Sunday
    n: positive for counting from the start (1=first, 2=second, ...),
       negative for counting from the end (-1=last, -2=second last, ...)
    
    Raises ValueError if n is 0 or that occurrence does not exist.
    """
    if n == 0:
        raise ValueError("n cannot be 0")
    
    # Get the number of days in the month
    num_days = calendar.monthrange(year, month)[1]
    
    # Get the weekday of the first day of the month (0=Monday ... 6=Sunday)
    first_weekday = calendar.weekday(year, month, 1)
    
    if n > 0:
        # Find the first occurrence of the given weekday
        # Days are 1-indexed, weekdays are 0-indexed (Monday=0)
        # The first day of the month has weekday first_weekday
        # We need to find the first day where weekday matches
        
        # Calculate how many days from the 1st to reach the target weekday
        diff = (weekday - first_weekday) % 7
        first_occurrence = 1 + diff
        
        # The n-th occurrence is first_occurrence + (n-1)*7
        day = first_occurrence + (n - 1) * 7
        
        if day > num_days:
            raise ValueError(f"The {n}-th {weekday} does not exist in {year}-{month}")
        
        return day
    else:
        # n is negative, count from the end
        # -1 means last, -2 means second last, etc.
        # Find the last occurrence of the given weekday
        
        # The last day of the month has weekday:
        last_weekday = calendar.weekday(year, month, num_days)
        
        # Calculate how many days from the last day to reach the target weekday
        # We want to go backwards from the last day
        diff = (last_weekday - weekday) % 7
        last_occurrence = num_days - diff
        
        # The n-th from the end (n is negative)
        # n = -1 -> last_occurrence
        # n = -2 -> last_occurrence - 7
        # n = -k -> last_occurrence - (k-1)*7
        k = -n
        day = last_occurrence - (k - 1) * 7
        
        if day < 1:
            raise ValueError(f"The {n}-th {weekday} does not exist in {year}-{month}")
        
        return day