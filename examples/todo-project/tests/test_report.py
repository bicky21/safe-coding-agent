from todo.report import summary
from todo.store import TodoStore


def test_empty_store():
    assert summary(TodoStore()) == "0 tasks: 0 done, 0 pending. Nothing pending."


def test_one_task():
    s = TodoStore()
    s.add("Buy milk")
    assert summary(s) == "1 task: 0 done, 1 pending. Next: Buy milk"


def test_mixed():
    s = TodoStore()
    s.add("Buy milk", priority=1)
    s.add("Write report", priority=3)
    s.add("Call mom", priority=1)
    s.complete(2)
    assert summary(s) == "3 tasks: 1 done, 2 pending. Next: Buy milk"


def test_all_done():
    s = TodoStore()
    s.add("A")
    s.add("B")
    s.complete(1)
    s.complete(2)
    assert summary(s) == "2 tasks: 2 done, 0 pending. Nothing pending."
