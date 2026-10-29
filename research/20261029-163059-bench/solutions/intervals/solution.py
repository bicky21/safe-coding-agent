def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    if not intervals:
        return []
    
    # Sort intervals by start time
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    
    # Initialize with the first interval
    merged = [sorted_intervals[0]]
    
    for current in sorted_intervals[1:]:
        last = merged[-1]
        # If current interval overlaps with or touches the last merged interval
        if current[0] <= last[1]:
            # Merge by updating the end time to the maximum of both ends
            last[1] = max(last[1], current[1])
        else:
            # No overlap, add the current interval as a new merged interval
            merged.append(current)
    
    return merged