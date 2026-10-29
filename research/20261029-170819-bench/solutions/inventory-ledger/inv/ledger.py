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
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ValueError("qty must be a positive int")

    @staticmethod
    def _to_decimal_cost(unit_cost):
        """Convert allowed cost types to Decimal, validating."""
        if isinstance(unit_cost, Decimal):
            dec = unit_cost
        elif isinstance(unit_cost, int):
            dec = Decimal(unit_cost)
        elif isinstance(unit_cost, str):
            try:
                dec = Decimal(unit_cost)
            except InvalidOperation:
                raise ValueError("unit_cost string is not a valid decimal")
        else:
            raise TypeError("unit_cost must be int, str, or Decimal (float not allowed)")

        if dec < 0:
            raise ValueError("unit_cost cannot be negative")
        return dec

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def receive(self, sku, qty, unit_cost):
        """Add a new lot for the given SKU."""
        self._validate_qty(qty)
        cost = self._to_decimal_cost(unit_cost)
        self._lots.setdefault(sku, []).append([qty, cost])

    def stock(self, sku):
        """Return total units left for the SKU (0 if unknown)."""
        return sum(q for q, _ in self._lots.get(sku, []))

    def sell(self, sku, qty):
        """Remove qty units FIFO and return total cost rounded to cents."""
        self._validate_qty(qty)
        lots = self._lots.get(sku, [])
        total_available = self.stock(sku)
        if qty > total_available:
            raise InsufficientStock(f"Not enough stock for SKU {sku}")

        remaining = qty
        total_cost = Decimal('0')
        # FIFO: consume from the front of the list
        while remaining > 0:
            lot_qty, lot_cost = lots[0]
            take = min(lot_qty, remaining)
            total_cost += lot_cost * take
            lot_qty -= take
            remaining -= take
            if lot_qty == 0:
                lots.pop(0)
            else:
                lots[0][0] = lot_qty

        # Round only the total
        total_cost = total_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return total_cost

    def value(self, sku):
        """Return total value of remaining stock for SKU, rounded to cents."""
        lots = self._lots.get(sku, [])
        if not lots:
            return Decimal('0.00')
        total = sum(Decimal(q) * cost for q, cost in lots)
        total = total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return total

    def transfer(self, sku, qty, other):
        """
        Move qty units from this ledger to another ledger, preserving FIFO order.
        Returns the total cost of transferred units, rounded like sell().
        """
        if not isinstance(other, Ledger):
            raise TypeError("other must be a Ledger instance")
        self._validate_qty(qty)
        lots = self._lots.get(sku, [])
        total_available = self.stock(sku)
        if qty > total_available:
            raise InsufficientStock(f"Not enough stock for SKU {sku}")

        remaining = qty
        transferred_cost = Decimal('0')
        transferred_lots = []  # list of [qty, cost] to add to other

        while remaining > 0:
            lot_qty, lot_cost = lots[0]
            take = min(lot_qty, remaining)
            transferred_cost += lot_cost * take
            transferred_lots.append([take, lot_cost])

            lot_qty -= take
            remaining -= take
            if lot_qty == 0:
                lots.pop(0)
            else:
                lots[0][0] = lot_qty

        # Add transferred lots to the other ledger preserving order
        for q, c in transferred_lots:
            other._lots.setdefault(sku, []).append([q, c])

        transferred_cost = transferred_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return transferred_cost

    def skus(self):
        """Return sorted list of SKUs that have stock > 0."""
        return sorted([sku for sku, lots in self._lots.items() if any(q > 0 for q, _ in lots)])