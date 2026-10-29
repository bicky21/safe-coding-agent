from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import List, Dict


class InsufficientStock(Exception):
    """Raised when attempting to sell or transfer more units than are available."""
    pass


class Ledger:
    """Tracks stock per SKU as lots of (quantity, unit cost)."""

    def __init__(self):
        # sku -> list of [qty, unit_cost] in FIFO order (oldest first)
        self._lots: Dict[str, List[List[int, Decimal]]] = {}

    # ------------------------------------------------------------------
    # Helper validation methods
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_qty(qty: int) -> None:
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ValueError("qty must be a positive int")

    @staticmethod
    def _validate_unit_cost(unit_cost) -> Decimal:
        if isinstance(unit_cost, float):
            raise TypeError("unit_cost cannot be a float")
        if isinstance(unit_cost, Decimal):
            cost = unit_cost
        elif isinstance(unit_cost, int):
            cost = Decimal(unit_cost)
        elif isinstance(unit_cost, str):
            try:
                cost = Decimal(unit_cost)
            except InvalidOperation:
                raise ValueError("unit_cost string is not a valid decimal")
        else:
            raise TypeError("unit_cost must be int, str, or Decimal")
        if cost < 0:
            raise ValueError("unit_cost cannot be negative")
        return cost

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def receive(self, sku: str, qty: int, unit_cost) -> None:
        """Adds a new lot."""
        self._validate_qty(qty)
        cost = self._validate_unit_cost(unit_cost)
        self._lots.setdefault(sku, []).append([qty, cost])

    def stock(self, sku: str) -> int:
        """Units left (0 for an unknown sku)."""
        return sum(q for q, _ in self._lots.get(sku, []))

    def sell(self, sku: str, qty: int) -> Decimal:
        """Removes qty units, oldest lots first (FIFO), and returns the cost."""
        self._validate_qty(qty)
        if qty > self.stock(sku):
            raise InsufficientStock("Not enough stock to sell")
        lots = self._lots.get(sku, [])
        remaining = qty
        total_cost = Decimal(0)
        # FIFO: process from the start of the list
        i = 0
        while remaining > 0 and i < len(lots):
            lot_qty, lot_cost = lots[i]
            take = min(lot_qty, remaining)
            total_cost += Decimal(take) * lot_cost
            lots[i][0] -= take
            remaining -= take
            if lots[i][0] == 0:
                # remove empty lot
                lots.pop(i)
                # do not increment i, as list shifted
            else:
                i += 1
        # round total cost to cents
        return total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def value(self, sku: str) -> Decimal:
        """Sum of qty * unit_cost of the remaining lots, rounded to cents."""
        lots = self._lots.get(sku, [])
        if not lots:
            return Decimal("0.00")
        total = sum(Decimal(q) * c for q, c in lots)
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def transfer(self, sku: str, qty: int, other: "Ledger") -> Decimal:
        """Moves qty units to the Ledger `other`, oldest first, keeping each unit's cost."""
        self._validate_qty(qty)
        if qty > self.stock(sku):
            raise InsufficientStock("Not enough stock to transfer")
        # Prepare transfer list
        lots = self._lots.get(sku, [])
        remaining = qty
        transfer_lots: List[List[int, Decimal]] = []
        i = 0
        while remaining > 0 and i < len(lots):
            lot_qty, lot_cost = lots[i]
            take = min(lot_qty, remaining)
            transfer_lots.append([take, lot_cost])
            lots[i][0] -= take
            remaining -= take
            if lots[i][0] == 0:
                lots.pop(i)
            else:
                i += 1
        # Apply to other ledger
        for t_qty, t_cost in transfer_lots:
            other._lots.setdefault(sku, []).append([t_qty, t_cost])
        # Compute total cost
        total_cost = sum(Decimal(t_qty) * t_cost for t_qty, t_cost in transfer_lots)
        return total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def skus(self) -> List[str]:
        """Sorted SKUs that have stock > 0."""
        return sorted([sku for sku, lots in self._lots.items() if self.stock(sku) > 0])