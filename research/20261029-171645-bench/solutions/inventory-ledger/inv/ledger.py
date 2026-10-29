from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import List, Dict


class InsufficientStock(Exception):
    """Raised when attempting to sell or transfer more units than are available."""
    pass


class Ledger:
    """Tracks stock per SKU as lots of (quantity, unit cost)."""

    def __init__(self):
        # sku -> list of [qty (int), unit_cost (Decimal)]
        # The list is ordered from oldest lot (index 0) to newest lot (last index)
        self._lots: Dict[str, List[List[int, Decimal]]] = {}

    # --------------------------------------------------------------------- #
    # Helper validation methods
    # --------------------------------------------------------------------- #
    @staticmethod
    def _validate_qty(qty):
        if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
            raise ValueError("qty must be a positive int")

    @staticmethod
    def _to_decimal_cost(unit_cost):
        if isinstance(unit_cost, float):
            raise TypeError("unit_cost must not be a float")
        try:
            if isinstance(unit_cost, Decimal):
                cost = unit_cost
            elif isinstance(unit_cost, int):
                cost = Decimal(unit_cost)
            elif isinstance(unit_cost, str):
                cost = Decimal(unit_cost)
            else:
                raise TypeError("unit_cost must be int, str, or Decimal")
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("unit_cost string must represent a valid decimal") from exc

        if cost < 0:
            raise ValueError("unit_cost cannot be negative")
        return cost

    @staticmethod
    def _round_money(value: Decimal) -> Decimal:
        """Round to two decimal places using ROUND_HALF_UP."""
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def receive(self, sku: str, qty: int, unit_cost):
        """Add a new lot to the ledger."""
        self._validate_qty(qty)
        cost = self._to_decimal_cost(unit_cost)
        self._lots.setdefault(sku, []).append([qty, cost])

    def stock(self, sku: str) -> int:
        """Return total units left for the given SKU."""
        return sum(q for q, _ in self._lots.get(sku, []))

    def sell(self, sku: str, qty: int) -> Decimal:
        """Remove qty units (FIFO) and return total cost rounded to cents."""
        self._validate_qty(qty)

        if self.stock(sku) < qty:
            raise InsufficientStock(f"Not enough stock for SKU {sku}")

        total_cost = Decimal("0")
        remaining = qty
        lots = self._lots[sku]

        # FIFO: consume from the oldest lot (index 0)
        while remaining > 0:
            lot_qty, lot_cost = lots[0]
            take = min(lot_qty, remaining)
            total_cost += lot_cost * take
            lot_qty -= take
            remaining -= take

            if lot_qty == 0:
                lots.pop(0)  # remove empty lot
            else:
                lots[0][0] = lot_qty  # update remaining qty in the lot

        # Clean up empty SKU entry
        if not lots:
            self._lots.pop(sku, None)

        return self._round_money(total_cost)

    def value(self, sku: str) -> Decimal:
        """Return total value of remaining stock for SKU, rounded to cents."""
        lots = self._lots.get(sku, [])
        if not lots:
            return Decimal("0.00")
        total = sum(Decimal(q) * cost for q, cost in lots)
        return self._round_money(total)

    def transfer(self, sku: str, qty: int, other: "Ledger") -> Decimal:
        """
        Move qty units to another Ledger, preserving FIFO order and unit costs.
        Returns the total cost of transferred units, rounded like sell().
        """
        self._validate_qty(qty)

        if self.stock(sku) < qty:
            raise InsufficientStock(f"Not enough stock for SKU {sku}")

        total_cost = Decimal("0")
        remaining = qty
        source_lots = self._lots[sku]

        # We'll collect transferred lots to add to the other ledger
        transferred_lots: List[List[int, Decimal]] = []

        while remaining > 0:
            lot_qty, lot_cost = source_lots[0]
            take = min(lot_qty, remaining)
            total_cost += lot_cost * take
            # Record the portion being transferred
            transferred_lots.append([take, lot_cost])

            lot_qty -= take
            remaining -= take

            if lot_qty == 0:
                source_lots.pop(0)
            else:
                source_lots[0][0] = lot_qty

        # Clean up empty SKU entry
        if not source_lots:
            self._lots.pop(sku, None)

        # Add transferred lots to the other ledger preserving order
        for qty_part, cost_part in transferred_lots:
            other._lots.setdefault(sku, []).append([qty_part, cost_part])

        return self._round_money(total_cost)

    def skus(self) -> List[str]:
        """Return sorted list of SKUs that have stock > 0."""
        return sorted([sku for sku, lots in self._lots.items() if lots])