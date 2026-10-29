from decimal import Decimal

import pytest

from inv.ledger import InsufficientStock, Ledger


@pytest.fixture
def ledger():
    l = Ledger()
    l.receive("apple", 10, "1.00")
    l.receive("apple", 5, "1.50")
    l.receive("pear", 3, 2)
    return l


def test_stock_and_unknown_sku(ledger):
    assert ledger.stock("apple") == 15
    assert ledger.stock("kiwi") == 0
    assert ledger.value("kiwi") == Decimal("0.00")


def test_sell_is_fifo_across_lots(ledger):
    assert ledger.sell("apple", 12) == Decimal("13.00")      # 10 x 1.00 + 2 x 1.50
    assert ledger.stock("apple") == 3
    assert ledger.value("apple") == Decimal("4.50")


def test_value_sums_all_lots(ledger):
    assert ledger.value("apple") == Decimal("17.50")
    assert isinstance(ledger.value("apple"), Decimal)


def test_money_is_exact_decimal():
    l = Ledger()
    for _ in range(3):
        l.receive("x", 1, "0.10")
    assert l.value("x") == Decimal("0.30")                    # float would give 0.30000000000000004
    assert l.sell("x", 3) == Decimal("0.30")


def test_rounds_the_total_half_up_not_each_lot():
    l = Ledger()
    l.receive("x", 1, "0.005")
    l.receive("x", 1, "0.005")
    assert l.sell("x", 2) == Decimal("0.01")                  # 0.010 total; per lot would be 0.02
    l.receive("y", 1, "0.125")
    assert l.sell("y", 1) == Decimal("0.13")                  # half UP, not banker's rounding


def test_insufficient_stock_changes_nothing(ledger):
    with pytest.raises(InsufficientStock):
        ledger.sell("apple", 16)
    with pytest.raises(InsufficientStock):
        ledger.sell("kiwi", 1)
    assert ledger.stock("apple") == 15 and ledger.value("apple") == Decimal("17.50")


@pytest.mark.parametrize("qty", [0, -1, 1.5, True, "3"])
def test_bad_quantities(ledger, qty):
    with pytest.raises(ValueError):
        ledger.receive("apple", qty, 1)
    with pytest.raises(ValueError):
        ledger.sell("apple", qty)


def test_bad_costs():
    l = Ledger()
    with pytest.raises(TypeError):
        l.receive("x", 1, 1.25)
    with pytest.raises(ValueError):
        l.receive("x", 1, "-1")
    assert l.stock("x") == 0


def test_transfer_keeps_costs_and_order(ledger):
    other = Ledger()
    other.receive("apple", 1, "9.00")
    assert ledger.transfer("apple", 12, other) == Decimal("13.00")
    assert ledger.stock("apple") == 3
    assert other.stock("apple") == 13
    assert other.sell("apple", 1) == Decimal("9.00")          # other's own older lot goes first
    assert other.sell("apple", 10) == Decimal("10.00")        # then the moved 10 x 1.00
    assert other.sell("apple", 2) == Decimal("3.00")          # then the moved 2 x 1.50


def test_transfer_errors_change_nothing(ledger):
    other = Ledger()
    with pytest.raises(InsufficientStock):
        ledger.transfer("pear", 4, other)
    assert ledger.stock("pear") == 3 and other.stock("pear") == 0


def test_skus(ledger):
    ledger.sell("pear", 3)
    assert ledger.skus() == ["apple"]
    ledger.receive("banana", 1, 1)
    assert ledger.skus() == ["apple", "banana"]
