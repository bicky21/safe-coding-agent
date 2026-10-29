from .ledger import Ledger
from decimal import Decimal


def valuation_report(ledger: Ledger) -> str:
    """Generate a valuation report for the given ledger."""
    lines = []
    header = f"{'SKU':<10}{'QTY':>6}{'VALUE':>14}"
    lines.append(header)
    total_qty = 0
    total_value = Decimal("0")
    for sku in ledger.skus():
        qty = ledger.stock(sku)
        value = ledger.value(sku)
        lines.append(f"{sku:<10}{qty:>6}{value:>14,.2f}")
        total_qty += qty
        total_value += value
    lines.append(f"{'TOTAL':<10}{total_qty:>6}{total_value:>14,.2f}")
    return "\n".join(lines)