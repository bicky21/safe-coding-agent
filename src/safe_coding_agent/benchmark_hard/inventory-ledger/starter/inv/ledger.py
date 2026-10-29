class InsufficientStock(Exception):
    pass


class Ledger:
    """Tracks stock per SKU as lots of (quantity, unit cost)."""

    def __init__(self):
        self._lots = {}          # sku -> list of [qty, unit_cost]

    def receive(self, sku, qty, unit_cost):
        self._lots.setdefault(sku, []).append([qty, float(unit_cost)])

    def stock(self, sku):
        return sum(q for q, _ in self._lots.get(sku, []))

    def sell(self, sku, qty):
        lots = self._lots.get(sku, [])
        cost = 0.0
        remaining = qty
        while remaining > 0 and lots:
            lot = lots[-1]
            take = min(lot[0], remaining)
            cost += take * lot[1]
            lot[0] -= take
            remaining -= take
            if lot[0] == 0:
                lots.pop()
        return round(cost, 2)

    def value(self, sku):
        lots = self._lots.get(sku, [])
        if not lots:
            return 0
        return round(self.stock(sku) * lots[-1][1], 2)
