"""Reference solution for the inventory-ledger task (used only to check the task's tests)."""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


class InsufficientStock(Exception):
    pass


def _qty(qty):
    if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
        raise ValueError(f"quantity must be a positive int, not {qty!r}")
    return qty


def _cost(cost):
    if isinstance(cost, float):
        raise TypeError("use Decimal, int or str for money, not float")
    if isinstance(cost, bool) or not isinstance(cost, (int, str, Decimal)):
        raise TypeError(f"bad cost {cost!r}")
    value = Decimal(cost)
    if value < 0:
        raise ValueError("cost must not be negative")
    return value


def _round(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


class Ledger:
    """Tracks stock per SKU as lots of (quantity, unit cost)."""

    def __init__(self):
        self._lots = {}          # sku -> list of [qty, unit_cost]

    def receive(self, sku, qty, unit_cost):
        self._lots.setdefault(sku, []).append([_qty(qty), _cost(unit_cost)])

    def stock(self, sku):
        return sum(q for q, _ in self._lots.get(sku, []))

    def _take(self, sku, qty):
        qty = _qty(qty)
        if qty > self.stock(sku):
            raise InsufficientStock(f"{sku}: wanted {qty}, have {self.stock(sku)}")
        lots, taken, remaining = self._lots[sku], [], qty
        while remaining:
            lot = lots[0]
            take = min(lot[0], remaining)
            taken.append((take, lot[1]))
            lot[0] -= take
            remaining -= take
            if lot[0] == 0:
                lots.pop(0)
        return taken

    def sell(self, sku, qty):
        return _round(sum((q * c for q, c in self._take(sku, qty)), Decimal(0)))

    def transfer(self, sku, qty, other):
        taken = self._take(sku, qty)
        for q, c in taken:
            other._lots.setdefault(sku, []).append([q, c])
        return _round(sum((q * c for q, c in taken), Decimal(0)))

    def value(self, sku):
        return _round(sum((q * c for q, c in self._lots.get(sku, [])), Decimal(0)))

    def skus(self):
        return sorted(s for s in self._lots if self.stock(s) > 0)
