import math
import re

class EvalError(Exception):
    pass

# Token types
NUMBER, NAME, OP, LPAREN, RPAREN, COMMA, EOF = (
    'NUMBER', 'NAME', 'OP', 'LPAREN', 'RPAREN', 'COMMA', 'EOF'
)

# Token regex patterns
_token_spec = [
    ('NUMBER', r'(?:(?:\d[\d_]*)(?:\.\d[\d_]*?)?|(?:\.\d[\d_]*))(?:[eE][+-]?\d+)?'),
    ('NAME',   r'[A-Za-z_][A-Za-z0-9_]*'),
    ('OP',     r'\*\*|//|[+\-*/%]'),
    ('LPAREN', r'\('),
    ('RPAREN', r'\)'),
    ('COMMA',  r','),
    ('SKIP',   r'[ \t]+'),
    ('MISMATCH', r'.'),
]

_token_re = re.compile('|'.join('(?P<%s>%s)' % pair for pair in _token_spec))

class Token:
    def __init__(self, typ, value, pos):
        self.type = typ
        self.value = value
        self.pos = pos

    def __repr__(self):
        return f'Token({self.type}, {self.value!r}, {self.pos})'

def tokenize(expr):
    pos = 0
    tokens = []
    while pos < len(expr):
        m = _token_re.match(expr, pos)
        if not m:
            raise EvalError(f"unexpected character '{expr[pos]}' at position {pos}")
        typ = m.lastgroup
        val = m.group(typ)
        if typ == 'SKIP':
            pos = m.end()
            continue
        if typ == 'MISMATCH':
            raise EvalError(f"unexpected character '{val}' at position {pos}")
        tokens.append(Token(typ, val, pos))
        pos = m.end()
    tokens.append(Token(EOF, None, pos))
    return tokens

class Parser:
    def __init__(self, tokens, variables):
        self.tokens = tokens
        self.variables = variables or {}
        self.pos = 0
        self.current = self.tokens[self.pos]

    def error(self, msg):
        raise EvalError(msg)

    def advance(self):
        self.pos += 1
        self.current = self.tokens[self.pos]

    def expect(self, typ, value=None):
        if self.current.type != typ or (value is not None and self.current.value != value):
            if self.current.type == EOF:
                self.error("unexpected end of expression")
            else:
                self.error(f"unexpected token '{self.current.value}' at position {self.current.pos}")
        self.advance()

    def parse(self):
        if self.current.type == EOF:
            self.error("unexpected end of expression")
        result = self.expr()
        if self.current.type != EOF:
            self.error(f"unexpected token '{self.current.value}' at position {self.current.pos}")
        return result

    # Grammar:
    # expr : term ((+|-) term)*
    # term : factor ((*|/|//|%) factor)*
    # factor : unary (** factor)*
    # unary : (+|-) unary | power
    # power : primary
    # primary : NUMBER | NAME | function_call | '(' expr ')'

    def expr(self):
        node = self.term()
        while self.current.type == OP and self.current.value in ('+', '-'):
            op = self.current.value
            pos = self.current.pos
            self.advance()
            right = self.term()
            if op == '+':
                node = node + right
            else:
                node = node - right
        return node

    def term(self):
        node = self.factor()
        while self.current.type == OP and self.current.value in ('*', '/', '//', '%'):
            op = self.current.value
            pos = self.current.pos
            self.advance()
            right = self.factor()
            if op == '*':
                node = node * right
            elif op == '/':
                if right == 0:
                    self.error(f"division by zero at position {pos}")
                node = node / right
            elif op == '//':
                if right == 0:
                    self.error(f"division by zero at position {pos}")
                node = math.floor(node / right)
            elif op == '%':
                if right == 0:
                    self.error(f"division by zero at position {pos}")
                node = node % right
        return node

    def factor(self):
        node = self.unary()
        if self.current.type == OP and self.current.value == '**':
            pos = self.current.pos
            self.advance()
            right = self.factor()  # right-associative
            node = node ** right
        return node

    def unary(self):
        if self.current.type == OP and self.current.value in ('+', '-'):
            op = self.current.value
            pos = self.current.pos
            self.advance()
            operand = self.unary()
            return +operand if op == '+' else -operand
        return self.primary()

    def primary(self):
        tok = self.current
        if tok.type == NUMBER:
            val = tok.value
            pos = tok.pos
            self.advance()
            if '.' in val or 'e' in val or 'E' in val:
                return float(val.replace('_', ''))
            else:
                return int(val.replace('_', ''))
        if tok.type == NAME:
            name = tok.value
            pos = tok.pos
            self.advance()
            if self.current.type == LPAREN:
                return self.function_call(name, pos)
            if name in self.variables:
                return self.variables[name]
            else:
                self.error(f"unknown name '{name}' at position {pos}")
        if tok.type == LPAREN:
            self.advance()
            val = self.expr()
            if self.current.type != RPAREN:
                self.error(f"unexpected token '{self.current.value}' at position {self.current.pos}")
            self.advance()
            return val
        self.error(f"unexpected token '{tok.value}' at position {tok.pos}")

    def function_call(self, name, name_pos):
        if name not in ('abs', 'min', 'max', 'round'):
            self.error(f"unknown function '{name}' at position {name_pos}")
        self.expect(LPAREN)
        args = []
        if self.current.type != RPAREN:
            while True:
                args.append(self.expr())
                if self.current.type == COMMA:
                    self.advance()
                else:
                    break
        self.expect(RPAREN)
        if name == 'abs':
            if len(args) != 1:
                self.error(f"wrong number of arguments for 'abs' at position {name_pos}")
            return abs(args[0])
        if name == 'min':
            if len(args) < 1:
                self.error(f"wrong number of arguments for 'min' at position {name_pos}")
            return min(args)
        if name == 'max':
            if len(args) < 1:
                self.error(f"wrong number of arguments for 'max' at position {name_pos}")
            return max(args)
        if name == 'round':
            if len(args) == 1:
                return round(args[0])
            if len(args) == 2:
                return round(args[0], int(args[1]))
            self.error(f"wrong number of arguments for 'round' at position {name_pos}")

def evaluate(expr: str, variables: dict | None = None) -> int | float:
    tokens = tokenize(expr)
    parser = Parser(tokens, variables)
    return parser.parse()