import pytest

from calc import EvalError, evaluate


@pytest.mark.parametrize("expr, expected", [
    ("1 + 2 * 3", 7),
    ("(1 + 2) * 3", 9),
    ("10 - 4 - 3", 3),
    ("2 ** 3 ** 2", 512),            # right to left
    ("-2 ** 2", -4),                 # ** binds tighter than unary minus
    ("(-2) ** 2", 4),
    ("2 ** -1", 0.5),
    ("--3", 3),
    ("-+-3", 3),
    ("7 / 2", 3.5),
    ("6 / 3", 2.0),
    ("7 // 2", 3),
    ("-7 // 2", -4),
    ("7 % -3", -2),
    ("1_000 + .5", 1000.5),
    ("2. * 1e3", 2000.0),
    ("2.5E-2 * 4", 0.1),
    ("\t1 +\t1 ", 2),
])
def test_arithmetic(expr, expected):
    result = evaluate(expr)
    assert result == expected and type(result) is type(expected)


def test_variables():
    assert evaluate("price * qty - discount", {"price": 2.5, "qty": 4, "discount": 1}) == 9.0
    assert evaluate("_x1 + x_2", {"_x1": 1, "x_2": 2}) == 3


@pytest.mark.parametrize("expr, expected", [
    ("abs(-3)", 3),
    ("min(3, 1, 2)", 1),
    ("max(2)", 2),
    ("round(2.567, 2)", 2.57),
    ("round(2.5)", 2),               # Python rounds half to even
    ("max(1, min(4, 2) * 3) + abs(-1)", 7),
])
def test_functions(expr, expected):
    result = evaluate(expr)
    assert result == expected and type(result) is type(expected)


@pytest.mark.parametrize("expr, message", [
    ("1 + $", "unexpected character '$' at position 4"),
    ("1 2", "unexpected token '2' at position 2"),
    ("(1 + 2", "unexpected end of expression"),
    ("", "unexpected end of expression"),
    ("1 + ", "unexpected end of expression"),
    ("1 + * 2", "unexpected token '*' at position 4"),
    ("(1))", "unexpected token ')' at position 3"),
    ("max(1,)", "unexpected token ')' at position 6"),
    ("2 * nope", "unknown name 'nope' at position 4"),
    ("foo(1)", "unknown function 'foo' at position 0"),
    ("1 + round(1, 2, 3)", "wrong number of arguments for 'round' at position 4"),
    ("min()", "wrong number of arguments for 'min' at position 0"),
    ("1 / 0", "division by zero at position 2"),
    ("5 // (2 - 2)", "division by zero at position 2"),
    ("1 + 5 % 0", "division by zero at position 6"),
])
def test_errors(expr, message):
    with pytest.raises(EvalError) as info:
        evaluate(expr)
    assert str(info.value) == message
