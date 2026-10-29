"""Reference solution for the expression-eval task (used only to check the task's tests)."""

import re


class EvalError(Exception):
    pass


_NUM = re.compile(r"(?:\d(?:_?\d)*(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
_NAME = re.compile(r"[A-Za-z_]\w*")
_OPS = ["**", "//", "+", "-", "*", "/", "%", "(", ")", ","]
_FUNCS = {"abs": (1, 1), "min": (1, None), "max": (1, None), "round": (1, 2)}


def _tokenize(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c in " \t":
            i += 1
            continue
        m = _NUM.match(s, i)
        if m:
            text = m.group()
            is_float = "." in text or "e" in text.lower()
            value = float(text.replace("_", "")) if is_float else int(text.replace("_", ""))
            out.append(("num", text, i, value))
            i = m.end()
            continue
        m = _NAME.match(s, i)
        if m:
            out.append(("name", m.group(), i, None))
            i = m.end()
            continue
        for op in _OPS:
            if s.startswith(op, i):
                out.append(("op", op, i, None))
                i += len(op)
                break
        else:
            raise EvalError(f"unexpected character '{c}' at position {i}")
    return out


class _Parser:
    def __init__(self, tokens, variables):
        self.t, self.i, self.vars = tokens, 0, variables

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self):
        tok = self.peek()
        if tok is None:
            raise EvalError("unexpected end of expression")
        self.i += 1
        return tok

    def is_op(self, *ops):
        tok = self.peek()
        return tok is not None and tok[0] == "op" and tok[1] in ops

    def expect(self, op):
        tok = self.take()
        if tok[0] != "op" or tok[1] != op:
            raise EvalError(f"unexpected token '{tok[1]}' at position {tok[2]}")

    def expr(self):
        value = self.term()
        while self.is_op("+", "-"):
            op = self.take()[1]
            rhs = self.term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def term(self):
        value = self.unary()
        while self.is_op("*", "/", "//", "%"):
            _, op, pos, _ = self.take()
            rhs = self.unary()
            if op == "*":
                value = value * rhs
                continue
            if rhs == 0:
                raise EvalError(f"division by zero at position {pos}")
            value = value / rhs if op == "/" else value // rhs if op == "//" else value % rhs
        return value

    def unary(self):
        if self.is_op("+", "-"):
            op = self.take()[1]
            value = self.unary()
            return -value if op == "-" else +value
        return self.power()

    def power(self):
        base = self.atom()
        if self.is_op("**"):
            self.take()
            return base ** self.unary()
        return base

    def atom(self):
        kind, text, pos, value = self.take()
        if kind == "num":
            return value
        if kind == "name":
            if self.is_op("("):
                self.take()
                args = []
                if not self.is_op(")"):
                    args.append(self.expr())
                    while self.is_op(","):
                        self.take()
                        args.append(self.expr())
                self.expect(")")
                if text not in _FUNCS:
                    raise EvalError(f"unknown function '{text}' at position {pos}")
                lo, hi = _FUNCS[text]
                if len(args) < lo or (hi is not None and len(args) > hi):
                    raise EvalError(f"wrong number of arguments for '{text}' at position {pos}")
                if text in ("min", "max"):
                    return (min if text == "min" else max)(args)     # also works for one argument
                return {"abs": abs, "round": round}[text](*args)
            if text not in self.vars:
                raise EvalError(f"unknown name '{text}' at position {pos}")
            return self.vars[text]
        if text == "(":
            value = self.expr()
            self.expect(")")
            return value
        raise EvalError(f"unexpected token '{text}' at position {pos}")


def evaluate(expr, variables=None):
    p = _Parser(_tokenize(expr), variables or {})
    value = p.expr()
    tok = p.peek()
    if tok is not None:
        raise EvalError(f"unexpected token '{tok[1]}' at position {tok[2]}")
    return value
