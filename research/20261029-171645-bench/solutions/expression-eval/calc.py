import math
import operator
from typing import Any, Callable, List, Tuple, Union

Number = Union[int, float]


class EvalError(Exception):
    """Exception raised for errors in the evaluation of an expression."""
    pass


# Token definitions
class Token:
    __slots__ = ("type", "value", "pos")

    def __init__(self, typ: str, value: Any, pos: int):
        self.type = typ      # e.g., 'NUMBER', 'NAME', 'OP', 'LPAREN', 'RPAREN', 'COMMA', 'EOF'
        self.value = value   # actual value (string or Number)
        self.pos = pos       # start position in the source string


class Lexer:
    _ops = {'+', '-', '*', '/', '%', '(', ')', ',', '//', '**'}

    def __init__(self, text: str):
        self.text = text
        self.length = len(text)
        self.idx = 0

    def _peek(self) -> str:
        return self.text[self.idx] if self.idx < self.length else ''

    def _advance(self, n: int = 1):
        self.idx += n

    def _skip_ws(self):
        while self.idx < self.length and self.text[self.idx] in ' \t':
            self.idx += 1

    def _error_unexpected_char(self, ch: str, pos: int):
        raise EvalError(f"unexpected character '{ch}' at position {pos}")

    def _error_unexpected_end(self):
        raise EvalError("unexpected end of expression")

    def _read_number(self, start: int) -> Token:
        i = start
        has_dot = False
        has_exp = False
        while i < self.length:
            ch = self.text[i]
            if ch.isdigit() or ch == '_' :
                i += 1
                continue
            if ch == '.':
                if has_dot:
                    break
                has_dot = True
                i += 1
                continue
            if ch in 'eE':
                if has_exp:
                    break
                has_exp = True
                i += 1
                # optional sign
                if i < self.length and self.text[i] in '+-':
                    i += 1
                continue
            break

        raw = self.text[start:i].replace('_', '')
        try:
            if has_dot or has_exp:
                value: Number = float(raw)
            else:
                value = int(raw, 10)
        except ValueError:
            self._error_unexpected_char(self.text[start], start)
        # advance lexer position
        self.idx = i
        return Token('NUMBER', value, start)

    def _read_name(self, start: int) -> Token:
        i = start
        while i < self.length and (self.text[i].isalnum() or self.text[i] == '_'):
            i += 1
        name = self.text[start:i]
        # advance lexer position
        self.idx = i
        return Token('NAME', name, start)

    def next_token(self) -> Token:
        self._skip_ws()
        if self.idx >= self.length:
            return Token('EOF', None, self.idx)

        ch = self.text[self.idx]
        pos = self.idx

        # Number (starts with digit or dot)
        if ch.isdigit() or (ch == '.' and self.idx + 1 < self.length and self.text[self.idx + 1].isdigit()):
            return self._read_number(pos)

        # Name
        if ch.isalpha() or ch == '_':
            return self._read_name(pos)

        # Operators and punctuation
        # Check two-char operators first
        two = self.text[self.idx:self.idx + 2]
        if two in ('//', '**'):
            self._advance(2)
            return Token('OP', two, pos)

        if ch in '+-*/%(),':
            self._advance()
            typ = 'OP' if ch in '+-*/%' else ('LPAREN' if ch == '(' else
                                            'RPAREN' if ch == ')' else 'COMMA')
            return Token(typ, ch, pos)

        # Anything else is unexpected
        self._error_unexpected_char(ch, pos)


class Parser:
    def __init__(self, lexer: Lexer, variables: dict):
        self.lexer = lexer
        self.variables = variables or {}
        self.current = self.lexer.next_token()

    def _eat(self, typ: str) -> Token:
        if self.current.type == typ:
            tok = self.current
            self.current = self.lexer.next_token()
            return tok
        else:
            if self.current.type == 'EOF' or self.current.value is None:
                raise EvalError("unexpected end of expression")
            raise EvalError(f"unexpected token '{self.current.value}' at position {self.current.pos}")

    def parse(self) -> Number:
        if self.current.type == 'EOF':
            raise EvalError("unexpected end of expression")
        result = self.expr()
        if self.current.type != 'EOF':
            if self.current.type == 'EOF' or self.current.value is None:
                raise EvalError("unexpected end of expression")
            raise EvalError(f"unexpected token '{self.current.value}' at position {self.current.pos}")
        return result

    # Grammar methods
    def expr(self) -> Number:
        node = self.term()
        while self.current.type == 'OP' and self.current.value in ('+', '-'):
            op = self.current
            self._eat('OP')
            right = self.term()
            if op.value == '+':
                node = node + right
            else:
                node = node - right
        return node

    def term(self) -> Number:
        node = self.unary()
        while self.current.type == 'OP' and self.current.value in ('*', '/', '//', '%'):
            op = self.current
            self._eat('OP')
            right = self.unary()
            if op.value == '*':
                node = node * right
            elif op.value == '/':
                if right == 0:
                    raise EvalError(f"division by zero at position {op.pos}")
                node = node / right
            elif op.value == '//':
                if right == 0:
                    raise EvalError(f"division by zero at position {op.pos}")
                node = operator.floordiv(node, right)
            else:  # '%'
                if right == 0:
                    raise EvalError(f"division by zero at position {op.pos}")
                node = operator.mod(node, right)
        return node

    def unary(self) -> Number:
        if self.current.type == 'OP' and self.current.value in ('+', '-'):
            op = self.current
            self._eat('OP')
            operand = self.unary()
            return +operand if op.value == '+' else -operand
        return self.power()

    def power(self) -> Number:
        node = self.primary()
        if self.current.type == 'OP' and self.current.value == '**':
            op = self.current
            self._eat('OP')
            right = self.power()
            node = node ** right
        return node

    def primary(self) -> Number:
        tok = self.current
        if tok.type == 'NUMBER':
            self._eat('NUMBER')
            return tok.value
        if tok.type == 'NAME':
            name_tok = self._eat('NAME')
            if self.current.type == 'LPAREN':
                # function call
                return self._call_function(name_tok)
            else:
                # variable
                if name_tok.value not in self.variables:
                    raise EvalError(f"unknown name '{name_tok.value}' at position {name_tok.pos}")
                val = self.variables[name_tok.value]
                if not isinstance(val, (int, float)):
                    raise EvalError(f"unknown name '{name_tok.value}' at position {name_tok.pos}")
                return val
        if tok.type == 'LPAREN':
            self._eat('LPAREN')
            val = self.expr()
            if self.current.type != 'RPAREN':
                raise EvalError(f"unexpected token '{self.current.value}' at position {self.current.pos}")
            self._eat('RPAREN')
            return val
        if tok.type == 'EOF':
            raise EvalError("unexpected end of expression")
        raise EvalError(f"unexpected token '{tok.value}' at position {tok.pos}")

    def _call_function(self, name_tok: Token) -> Number:
        func_name = name_tok.value
        pos = name_tok.pos
        self._eat('LPAREN')
        args = []
        if self.current.type == 'RPAREN':
            # No arguments
            self._eat('RPAREN')
            raise EvalError(f"wrong number of arguments for '{func_name}' at position {pos}")
        while True:
            args.append(self.expr())
            if self.current.type == 'COMMA':
                self._eat('COMMA')
                continue
            elif self.current.type == 'RPAREN':
                self._eat('RPAREN')
                break
            else:
                raise EvalError(f"unexpected token '{self.current.value}' at position {self.current.pos}")

        # Validate function
        if func_name == 'abs':
            if len(args) != 1:
                raise EvalError(f"wrong number of arguments for '{func_name}' at position {pos}")
            return abs(args[0])
        elif func_name == 'min':
            if len(args) < 1:
                raise EvalError(f"wrong number of arguments for '{func_name}' at position {pos}")
            return min(args)
        elif func_name == 'max':
            if len(args) < 1:
                raise EvalError(f"wrong number of arguments for '{func_name}' at position {pos}")
            return max(args)
        elif func_name == 'round':
            if len(args) == 1:
                return round(args[0])
            elif len(args) == 2:
                return round(args[0], int(args[1]))
            else:
                raise EvalError(f"wrong number of arguments for '{func_name}' at position {pos}")
        else:
            raise EvalError(f"unknown function '{func_name}' at position {pos}")


def evaluate(expr: str, variables: dict | None = None) -> int | float:
    """
    Evaluate a mathematical expression according to the specification.
    """
    lexer = Lexer(expr)
    parser = Parser(lexer, variables or {})
    result = parser.parse()
    return result