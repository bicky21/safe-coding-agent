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

    def complete(self, item_id: int) -> None:
        if item_id not in self._items:
            raise KeyError(f"Item with id {item_id} not found")
        self._items[item_id].done = True

    def remove(self, item_id: int) -> None:
        if item_id not in self._items:
            raise KeyError(f"Item with id {item_id} not found")
        del self._items[item_id]

    def pending(self) -> list[Item]:
        """Items that are not done, highest priority first, then oldest first (lowest id) for equal priority."""
        pending_items = [item for item in self._items.values() if not item.done]
        return sorted(pending_items, key=lambda item: (item.priority, item.id))