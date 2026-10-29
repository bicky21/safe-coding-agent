import operator
from typing import Any, Dict, Union

Number = Union[int, float]


class EvalError(Exception):
    """Exception raised for errors in the evaluation of an expression."""
    pass


# Token definitions
class Token:
    __slots__ = ("type", "value", "pos")

    def __init__(self, typ: str, value: Any, pos: int):
        self.type = typ      # e.g., 'NUMBER', 'NAME', 'OP', 'LPAREN', 'RPAREN', 'COMMA', 'EOF'
        self.value = value   # actual string or numeric value
        self.pos = pos       # start position in the original string


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

    def _error_unexpected_char(self, ch: str):
        raise EvalError(f"unexpected character '{ch}' at position {self.idx}")

    def _read_number(self) -> Token:
        start = self.idx
        has_dot = False
        has_exp = False
        while self.idx < self.length:
            ch = self.text[self.idx]
            if ch.isdigit() or ch == '_' :
                self.idx += 1
            elif ch == '.':
                if has_dot:
                    break
                has_dot = True
                self.idx += 1
            elif ch in 'eE':
                if has_exp:
                    break
                has_exp = True
                self.idx += 1
                if self.idx < self.length and self.text[self.idx] in '+-':
                    self.idx += 1
            else:
                break
        num_str = self.text[start:self.idx].replace('_', '')
        try:
            if not has_dot and not has_exp:
                value = int(num_str)
            else:
                value = float(num_str)
        except ValueError:
            self._error_unexpected_char(self.text[start])
        return Token('NUMBER', value, start)

    def _read_name(self) -> Token:
        start = self.idx
        while self.idx < self.length:
            ch = self.text[self.idx]
            if ch.isalnum() or ch == '_':
                self.idx += 1
            else:
                break
        name = self.text[start:self.idx]
        return Token('NAME', name, start)

    def next_token(self) -> Token:
        self._skip_ws()
        if self.idx >= self.length:
            return Token('EOF', None, self.idx)

        ch = self.text[self.idx]

        if ch.isdigit() or (ch == '.' and self.idx + 1 < self.length and self.text[self.idx + 1].isdigit()):
            return self._read_number()

        if ch.isalpha() or ch == '_':
            return self._read_name()

        if self.text.startswith('**', self.idx):
            tok = Token('OP', '**', self.idx)
            self._advance(2)
            return tok
        if self.text.startswith('//', self.idx):
            tok = Token('OP', '//', self.idx)
            self._advance(2)
            return tok

        if ch in '+-*/%(),':
            typ = 'OP' if ch in '+-*/%' else ('LPAREN' if ch == '(' else
                                            ('RPAREN' if ch == ')' else 'COMMA'))
            tok = Token(typ, ch, self.idx)
            self._advance()
            return tok

        self._error_unexpected_char(ch)


class Parser:
    def __init__(self, lexer: Lexer, variables: Dict[str, Any]):
        self.lexer = lexer
        self.variables = variables or {}
        self.current = self.lexer.next_token()

    def _eat(self, typ: str) -> Token:
        if self.current.type == typ:
            tok = self.current
            self.current = self.lexer.next_token()
            return tok
        else:
            txt = self.current.value if self.current.value is not None else ''
            raise EvalError(f"unexpected token '{txt}' at position {self.current.pos}")

    def parse(self) -> Number:
        if self.current.type == 'EOF':
            raise EvalError("unexpected end of expression")
        result = self.expr()
        if self.current.type != 'EOF':
            txt = self.current.value if self.current.value is not None else ''
            raise EvalError(f"unexpected token '{txt}' at position {self.current.pos}")
        return result

    # Grammar methods
    def expr(self) -> Number:
        node = self.term()
        while self.current.type == 'OP' and self.current.value in ('+', '-'):
            op_tok = self._eat('OP')
            right = self.term()
            node = node + right if op_tok.value == '+' else node - right
        return node

    def term(self) -> Number:
        node = self.factor()
        while self.current.type == 'OP' and self.current.value in ('*', '/', '//', '%'):
            op_tok = self._eat('OP')
            right = self.factor()
            if op_tok.value == '*':
                node = node * right
            elif op_tok.value == '/':
                if right == 0:
                    raise EvalError(f"division by zero at position {op_tok.pos}")
                node = node / right
            elif op_tok.value == '//':
                if right == 0:
                    raise EvalError(f"division by zero at position {op_tok.pos}")
                node = operator.floordiv(node, right)
            else:  # '%'
                if right == 0:
                    raise EvalError(f"division by zero at position {op_tok.pos}")
                node = operator.mod(node, right)
        return node

    def factor(self) -> Number:
        # handles exponentiation, right-associative
        node = self.unary()
        if self.current.type == 'OP' and self.current.value == '**':
            op_tok = self._eat('OP')
            right = self.factor()
            node = node ** right
        return node

    def unary(self) -> Number:
        if self.current.type == 'OP' and self.current.value in ('+', '-'):
            op_tok = self._eat('OP')
            operand = self.unary()
            return +operand if op_tok.value == '+' else -operand
        return self.primary()

    def primary(self) -> Number:
        tok = self.current
        if tok.type == 'NUMBER':
            self._eat('NUMBER')
            return tok.value
        if tok.type == 'NAME':
            name_tok = self._eat('NAME')
            if self.current.type == 'LPAREN':
                return self._call_function(name_tok)
            else:
                if name_tok.value not in self.variables:
                    raise EvalError(f"unknown name '{name_tok.value}' at position {name_tok.pos}")
                val = self.variables[name_tok.value]
                if not isinstance(val, (int, float)):
                    raise EvalError(f"unknown name '{name_tok.value}' at position {name_tok.pos}")
                return val
        if tok.type == 'LPAREN':
            self._eat('LPAREN')
            val = self.expr()
            if self.current.type == 'EOF':
                raise EvalError("unexpected end of expression")
            if self.current.type != 'RPAREN':
                raise EvalError(f"unexpected token '{self.current.value}' at position {self.current.pos}")
            self._eat('RPAREN')
            return val
        raise EvalError(f"unexpected token '{tok.value}' at position {tok.pos}")

    def _call_function(self, name_tok: Token) -> Number:
        func_name = name_tok.value
        pos = name_tok.pos
        self._eat('LPAREN')
        args = []
        if self.current.type == 'RPAREN':
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


def evaluate(expr: str, variables: Dict[str, Any] | None = None) -> Number:
    lexer = Lexer(expr)
    parser = Parser(lexer, variables or {})
    return parser.parse()