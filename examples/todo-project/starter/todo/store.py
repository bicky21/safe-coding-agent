from dataclasses import dataclass


@dataclass
class Item:
    id: int
    title: str
    priority: int = 0      # higher = more important
    done: bool = False


class TodoStore:
    def __init__(self):
        self._items: dict[int, Item] = {}
        self._next_id = 1

    def add(self, title: str, priority: int = 0) -> Item:
        if not title.strip():
            raise ValueError("title must not be empty")
        item = Item(self._next_id, title.strip(), priority)
        self._items[item.id] = item
        self._next_id += 1
        return item

    def items(self) -> list[Item]:
        """All items, oldest first."""
        return list(self._items.values())
