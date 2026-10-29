import pytest

from todo.store import TodoStore


@pytest.fixture
def store():
    s = TodoStore()
    s.add("Buy milk", priority=1)
    s.add("Write report", priority=3)
    s.add("Call mom", priority=1)
    return s


def test_add_and_items_still_work(store):
    assert [i.title for i in store.items()] == ["Buy milk", "Write report", "Call mom"]
    assert [i.id for i in store.items()] == [1, 2, 3]


def test_add_rejects_empty_title():
    with pytest.raises(ValueError):
        TodoStore().add("  ")


def test_complete_marks_done(store):
    store.complete(2)
    assert store.items()[1].done is True


def test_complete_unknown_id(store):
    with pytest.raises(KeyError):
        store.complete(99)


def test_remove(store):
    store.remove(1)
    assert [i.id for i in store.items()] == [2, 3]


def test_remove_unknown_id(store):
    with pytest.raises(KeyError):
        store.remove(99)


def test_ids_not_reused_after_remove(store):
    store.remove(3)
    assert store.add("New").id == 4


def test_pending_order(store):
    assert [i.title for i in store.pending()] == ["Write report", "Buy milk", "Call mom"]


def test_pending_skips_done(store):
    store.complete(2)
    assert [i.title for i in store.pending()] == ["Buy milk", "Call mom"]
