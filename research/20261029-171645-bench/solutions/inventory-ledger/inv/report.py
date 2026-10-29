from decimal import Decimal
from typing import List
from .ledger import Ledger


def valuation_report(ledger: Ledger) -> str:
    """
    Produce a valuation report string.

    Header:
        SKU        QTY        VALUE
    One line per SKU (sorted via ledger.skus()), then a TOTAL line.
    Values are formatted with commas and two decimal places.
    No trailing newline.
    """
    lines: List[str] = []
    header = f"{'SKU':<10}{'QTY':>6}{'VALUE':>14}"
    lines.append(header)

    total_qty = 0
    total_value = Decimal("0.00")

    for sku in ledger.skus():
        qty = ledger.stock(sku)
        value = ledger.value(sku)
        total_qty += qty
        total_value += value
        # format value with commas and two decimals
        value_str = f"{value:,.2f}"
        lines.append(f"{sku:<10}{qty:>6}{value_str:>14}")

    total_value_str = f"{total_value:,.2f}"
    lines.append(f"{'TOTAL':<10}{total_qty:>6}{total_value_str:>14}")

    return "\n".join(lines)