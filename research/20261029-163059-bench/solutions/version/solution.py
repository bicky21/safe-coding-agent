def compare_versions(a: str, b: str) -> int:
    def parse(version: str):
        # Split off pre-release label if present
        if '-' in version:
            main_part, label = version.split('-', 1)
        else:
            main_part, label = version, None
        
        # Parse numeric parts
        parts = main_part.split('.')
        nums = []
        for p in parts:
            if p == '':
                nums.append(0)
            else:
                nums.append(int(p))
        
        return nums, label
    
    nums_a, label_a = parse(a)
    nums_b, label_b = parse(b)
    
    # Compare numeric parts, padding with zeros
    max_len = max(len(nums_a), len(nums_b))
    for i in range(max_len):
        na = nums_a[i] if i < len(nums_a) else 0
        nb = nums_b[i] if i < len(nums_b) else 0
        if na < nb:
            return -1
        elif na > nb:
            return 1
    
    # Numeric parts are equal; now compare pre-release labels
    # A version with a pre-release label is LOWER than the same version without a label
    if label_a is None and label_b is None:
        return 0
    if label_a is None and label_b is not None:
        # a has no label, b has a label -> a > b
        return 1
    if label_a is not None and label_b is None:
        # a has a label, b has no label -> a < b
        return -1
    
    # Both have labels: compare alphabetically
    if label_a < label_b:
        return -1
    elif label_a > label_b:
        return 1
    else:
        return 0