"""Reference solution for the inventory-ledger task (used only to check the task's tests)."""

from decimal import Decimal


def valuation_report(ledger):
    lines = [f"{'SKU':<10}{'QTY':>6}{'VALUE':>14}"]
    total_qty, total_value = 0, Decimal("0.00")
    for sku in ledger.skus():
        qty, value = ledger.stock(sku), ledger.value(sku)
        total_qty += qty
        total_value += value
        lines.append(f"{sku:<10}{qty:>6}{value:>14,.2f}")
    lines.append(f"{'TOTAL':<10}{total_qty:>6}{total_value:>14,.2f}")
    return "\n".join(lines)
