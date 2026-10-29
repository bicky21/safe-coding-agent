from collections import OrderedDict

class LRUCache:
    """
    Least Recently Used (LRU) cache implementation.

    Attributes
    ----------
    capacity : int
        Maximum number of items the cache can hold.
    cache : OrderedDict
        Stores key-value pairs in order of usage, with the most recently used
        item at the end.
    """

    def __init__(self, capacity: int):
        """
        Initialize the LRU cache with a given capacity.

        Parameters
        ----------
        capacity : int
            The maximum number of key-value pairs the cache can store.
        """
        if capacity <= 0:
            raise ValueError("Capacity must be a positive integer")
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key: int) -> int:
        """
        Retrieve the value associated with the given key.

        If the key exists, it is marked as recently used.
        If the key does not exist, return -1.

        Parameters
        ----------
        key : int
            The key to look up.

        Returns
        -------
        int
            The value associated with the key, or -1 if the key is not present.
        """
        if key not in self.cache:
            return -1
        # Move the key to the end to mark it as recently used
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: int, value: int) -> None:
        """
        Insert or update the value for a key in the cache.

        If the key already exists, its value is updated and it is marked as
        recently used. If the key does not exist and the cache is at capacity,
        the least recently used item is evicted before inserting the new item.

        Parameters
        ----------
        key : int
            The key to insert or update.
        value : int
            The value to associate with the key.
        """
        if key in self.cache:
            # Update existing key and mark as recently used
            self.cache.move_to_end(key)
            self.cache[key] = value
            return

        if len(self.cache) >= self.capacity:
            # Evict the least recently used item (first item in OrderedDict)
            self.cache.popitem(last=False)

        self.cache[key] = value