from decimal import Decimal
from typing import List

def valuation_report(ledger) -> str:
    """
    Generate a valuation report for the given ledger.

    The report consists of a header line, one line per SKU (sorted by ledger.skus()),
    and a final TOTAL line. Values are formatted with commas and two decimal places.
    No trailing newline.
    """
    header = f"{'SKU':<10}{'QTY':>6}{'VALUE':>14}"
    lines: List[str] = [header]

    total_qty = 0
    total_value = Decimal('0.00')

    for sku in ledger.skus():
        qty = ledger.stock(sku)
        value = ledger.value(sku)
        total_qty += qty
        total_value += value
        lines.append(f"{sku:<10}{qty:>6}{value:>14,.2f}")

    total_value = total_value.quantize(Decimal('0.01'))
    lines.append(f"{'TOTAL':<10}{total_qty:>6}{total_value:>14,.2f}")

    return "\n".join(lines)