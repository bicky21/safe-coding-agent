import pytest

from solution import LRUCache


def test_get_missing_key():
    assert LRUCache(2).get(1) == -1


def test_get_after_put():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    assert c.get(1) == 1
    assert c.get(2) == 2


def test_evicts_least_recently_used():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    c.put(3, 3)          # removes key 1
    assert c.get(1) == -1
    assert c.get(3) == 3


def test_get_counts_as_use():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    c.get(1)
    c.put(3, 3)          # removes key 2, because 1 was used more recently
    assert c.get(2) == -1
    assert c.get(1) == 1


def test_update_counts_as_use():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    c.put(1, 10)         # update counts as use
    c.put(3, 3)          # removes key 2
    assert c.get(2) == -1
    assert c.get(1) == 10


def test_capacity_one():
    c = LRUCache(1)
    c.put(1, 1)
    c.put(2, 2)
    assert c.get(1) == -1
    assert c.get(2) == 2


def test_long_sequence():
    c = LRUCache(2)
    c.put(1, 1); c.put(2, 2)
    assert c.get(1) == 1
    c.put(3, 3)
    assert c.get(2) == -1
    c.put(4, 4)
    assert c.get(1) == -1
    assert c.get(3) == 3
    assert c.get(4) == 4
