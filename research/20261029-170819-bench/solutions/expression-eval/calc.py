import re
from typing import Any, Callable, List, Tuple, Union

class EvalError(Exception):
    """Exception raised for errors during evaluation."""
    pass

# Token definitions
Token = Tuple[str, str, int]  # (type, text, position)

TOKEN_SPEC = [
    ('NUMBER',   r'(?:\d[\d_]*\d|\d)(?:\.\d[\d_]*|\.\d|\.|\d[\d_]*\.\d[\d_]*|\d[\d_]*)(?:[eE][+-]?\d[\d_]*)?'),  # numbers with optional underscores
    ('NUMBER',   r'\d[\d_]*'),  # integer fallback
    ('NAME',     r'[A-Za-z_][A-Za-z0-9_]*'),
    ('OP',       r'\*\*|//|[+\-*/%]'),
    ('LPAREN',   r'\('),
    ('RPAREN',   r'\)'),
    ('COMMA',    r','),
    ('SKIP',     r'[ \t]+'),
]

TOKEN_REGEX = re.compile('|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_SPEC))

def tokenize(expr: str) -> List[Token]:
    pos = 0
    tokens: List[Token] = []
    while pos < len(expr):
        m = TOKEN_REGEX.match(expr, pos)
        if not m:
            raise EvalError(f"unexpected character '{expr[pos]}' at position {pos}")
        typ = m.lastgroup
        text = m.group(typ)
        if typ == 'SKIP':
            pos = m.end()
            continue
        if typ == 'NUMBER':
            # normalize underscores
            text = text.replace('_', '')
        tokens.append((typ, text, pos))
        pos = m.end()
    tokens.append(('EOF', '', len(expr)))
    return tokens

# Parser / evaluator
class Parser:
    def __init__(self, tokens: List[Token], variables: dict):
        self.tokens = tokens
        self.pos = 0
        self.variables = variables or {}

    def current(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> None:
        self.pos += 1

    def expect(self, typ: str) -> Token:
        token = self.current()
        if token[0] != typ:
            if token[0] == 'EOF':
                raise EvalError("unexpected end of expression")
            raise EvalError(f"unexpected token '{token[1]}' at position {token[2]}")
        self.advance()
        return token

    # Grammar entry
    def parse(self) -> Union[int, float]:
        result = self.expr()
        if self.current()[0] != 'EOF':
            token = self.current()
            raise EvalError(f"unexpected token '{token[1]}' at position {token[2]}")
        return result

    # expr -> term ((+|-) term)*
    def expr(self) -> Union[int, float]:
        left = self.term()
        while True:
            token = self.current()
            if token[0] == 'OP' and token[1] in ('+', '-'):
                op = token[1]
                self.advance()
                right = self.term()
                if op == '+':
                    left = left + right
                else:
                    left = left - right
            else:
                break
        return left

    # term -> factor ((*|/|//|%) factor)*
    def term(self) -> Union[int, float]:
        left = self.factor()
        while True:
            token = self.current()
            if token[0] == 'OP' and token[1] in ('*', '/', '//', '%'):
                op = token[1]
                self.advance()
                right = self.factor()
                if op == '*':
                    left = left * right
                elif op == '/':
                    if right == 0:
                        raise EvalError(f"division by zero at position {token[2]}")
                    left = left / right
                elif op == '//':
                    if right == 0:
                        raise EvalError(f"division by zero at position {token[2]}")
                    left = left // right
                else:  # %
                    if right == 0:
                        raise EvalError(f"division by zero at position {token[2]}")
                    left = left % right
            else:
                break
        return left

    # factor -> power
    def factor(self) -> Union[int, float]:
        return self.power()

    # power -> unary (** power)*
    def power(self) -> Union[int, float]:
        left = self.unary()
        token = self.current()
        if token[0] == 'OP' and token[1] == '**':
            self.advance()
            right = self.power()  # right-associative
            left = left ** right
        return left

    # unary -> (+|-) unary | primary
    def unary(self) -> Union[int, float]:
        token = self.current()
        if token[0] == 'OP' and token[1] in ('+', '-'):
            op = token[1]
            self.advance()
            operand = self.unary()
            return +operand if op == '+' else -operand
        return self.primary()

    # primary -> NUMBER | NAME (call?) | '(' expr ')'
    def primary(self) -> Union[int, float]:
        token = self.current()
        if token[0] == 'NUMBER':
            self.advance()
            txt = token[1]
            if '.' in txt or 'e' in txt or 'E' in txt:
                return float(txt)
            else:
                return int(txt)
        if token[0] == 'NAME':
            name = token[1]
            pos = token[2]
            self.advance()
            if self.current()[0] == 'LPAREN':
                # function call
                return self.call_function(name, pos)
            else:
                # variable
                if name not in self.variables:
                    raise EvalError(f"unknown name '{name}' at position {pos}")
                return self.variables[name]
        if token[0] == 'LPAREN':
            self.advance()
            val = self.expr()
            if self.current()[0] != 'RPAREN':
                raise EvalError(f"unexpected token '{self.current()[1]}' at position {self.current()[2]}")
            self.advance()
            return val
        if token[0] == 'EOF':
            raise EvalError("unexpected end of expression")
        raise EvalError(f"unexpected token '{token[1]}' at position {token[2]}")

    def call_function(self, name: str, name_pos: int) -> Union[int, float]:
        allowed: dict[str, Callable] = {
            'abs': abs,
            'min': min,
            'max': max,
            'round': round,
        }
        if name not in allowed:
            raise EvalError(f"unknown function '{name}' at position {name_pos}")
        # consume '('
        self.expect('LPAREN')
        args = []
        if self.current()[0] == 'RPAREN':
            # no arguments
            self.advance()
            raise EvalError(f"wrong number of arguments for '{name}' at position {name_pos}")
        while True:
            args.append(self.expr())
            if self.current()[0] == 'COMMA':
                self.advance()
                continue
            if self.current()[0] == 'RPAREN':
                self.advance()
                break
            else:
                raise EvalError(f"unexpected token '{self.current()[1]}' at position {self.current()[2]}")
        # check argument count
        if name in ('abs',):
            if len(args) != 1:
                raise EvalError(f"wrong number of arguments for '{name}' at position {name_pos}")
        elif name == 'round':
            if not (1 <= len(args) <= 2):
                raise EvalError(f"wrong number of arguments for '{name}' at position {name_pos}")
        else:  # min, max require at least 1
            if len(args) < 1:
                raise EvalError(f"wrong number of arguments for '{name}' at position {name_pos}")
        try:
            result = allowed[name](*args)
        except ZeroDivisionError:
            # round, min, max, abs don't raise division errors, but guard anyway
            raise EvalError(f"division by zero at position {name_pos}")
        # Ensure int stays int where appropriate (Python's builtins already do)
        return result

def evaluate(expr: str, variables: dict | None = None) -> int | float:
    tokens = tokenize(expr)
    parser = Parser(tokens, variables or {})
    result = parser.parse()
    return result