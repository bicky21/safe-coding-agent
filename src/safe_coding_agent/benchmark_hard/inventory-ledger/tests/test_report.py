from inv.ledger import Ledger
from inv.report import valuation_report


def test_report_format():
    l = Ledger()
    l.receive("pear", 3, "2.00")
    l.receive("apple", 1000, "1234.50")
    l.receive("apple", 5, "1.50")
    l.receive("empty", 2, 1)
    l.sell("empty", 2)                      # sold out: not listed
    assert valuation_report(l) == (
        "SKU          QTY         VALUE\n"
        "apple       1005  1,234,507.50\n"
        "pear           3          6.00\n"
        "TOTAL       1008  1,234,513.50"
    )


def test_empty_report():
    assert valuation_report(Ledger()) == "SKU          QTY         VALUE\nTOTAL          0          0.00"
