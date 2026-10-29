import math
from typing import Dict, Optional, Tuple, List, Union

class EvalError(Exception):
    pass

# Token types
NUMBER = 'NUMBER'
NAME = 'NAME'
OP = 'OP'
LPAREN = 'LPAREN'
RPAREN = 'RPAREN'
COMMA = 'COMMA'
EOF = 'EOF'

Token = Tuple[str, str, int]  # (type, value, position)

def tokenize(expr: str) -> List[Token]:
    tokens: List[Token] = []
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c.isspace():
            i += 1
            continue
        pos = i
        if c.isdigit() or (c == '.' and i+1 < n and expr[i+1].isdigit()):
            # number
            start = i
            has_dot = False
            has_exp = False
            if c == '.':
                has_dot = True
                i += 1
            while i < n and (expr[i].isdigit() or expr[i] == '_'):
                i += 1
            if i < n and expr[i] == '.':
                if has_dot:
                    raise EvalError(f"unexpected character '.' at position {i}")
                has_dot = True
                i += 1
                while i < n and (expr[i].isdigit() or expr[i] == '_'):
                    i += 1
            if i < n and expr[i] in 'eE':
                has_exp = True
                i += 1
                if i < n and expr[i] in '+-':
                    i += 1
                if i >= n or not expr[i].isdigit():
                    raise EvalError(f"unexpected character '{expr[i] if i<n else ''}' at position {i}")
                while i < n and (expr[i].isdigit() or expr[i] == '_'):
                    i += 1
            num_str = expr[start:i].replace('_', '')
            try:
                if has_dot or has_exp:
                    value = float(num_str)
                else:
                    value = int(num_str)
            except ValueError:
                raise EvalError(f"unexpected character '{expr[i-1]}' at position {i-1}")
            tokens.append((NUMBER, str(value), pos))
            continue
        if c.isalpha() or c == '_':
            start = i
            i += 1
            while i < n and (expr[i].isalnum() or expr[i] == '_'):
                i += 1
            name = expr[start:i]
            tokens.append((NAME, name, pos))
            continue
        if c == '(':
            tokens.append((LPAREN, c, pos))
            i += 1
            continue
        if c == ')':
            tokens.append((RPAREN, c, pos))
            i += 1
            continue
        if c == ',':
            tokens.append((COMMA, c, pos))
            i += 1
            continue
        # operators
        if c in '+-*/%':
            # check for // or **
            if c == '/' and i+1 < n and expr[i+1] == '/':
                tokens.append((OP, '//', pos))
                i += 2
            elif c == '*' and i+1 < n and expr[i+1] == '*':
                tokens.append((OP, '**', pos))
                i += 2
            else:
                tokens.append((OP, c, pos))
                i += 1
            continue
        raise EvalError(f"unexpected character '{c}' at position {pos}")
    tokens.append((EOF, '', n))
    return tokens

class Parser:
    def __init__(self, tokens: List[Token], variables: Optional[Dict[str, Union[int, float]]]):
        self.tokens = tokens
        self.pos = 0
        self.variables = variables or {}

    def current(self) -> Token:
        return self.tokens[self.pos]

    def consume(self, expected_type: str = None, expected_value: str = None) -> Token:
        tok = self.current()
        if expected_type and tok[0] != expected_type:
            raise EvalError(f"unexpected token '{tok[1]}' at position {tok[2]}")
        if expected_value and tok[1] != expected_value:
            raise EvalError(f"unexpected token '{tok[1]}' at position {tok[2]}")
        self.pos += 1
        return tok

    def parse(self) -> Union[int, float]:
        if self.current()[0] == EOF:
            raise EvalError("unexpected end of expression")
        result = self.expr()
        if self.current()[0] != EOF:
            raise EvalError(f"unexpected token '{self.current()[1]}' at position {self.current()[2]}")
        return result

    # expr: term ((+|-) term)*
    def expr(self):
        node = self.term()
        while self.current()[0] == OP and self.current()[1] in '+-':
            op_tok = self.consume(OP)
            if self.current()[0] == EOF:
                raise EvalError("unexpected end of expression")
            right = self.term()
            if op_tok[1] == '+':
                node = node + right
            else:
                node = node - right
        return node

    # term: factor ((*|/|//|%) factor)*
    def term(self):
        node = self.factor()
        while self.current()[0] == OP and self.current()[1] in '*///%':
            op_tok = self.consume(OP)
            if self.current()[0] == EOF:
                raise EvalError("unexpected end of expression")
            right = self.factor()
            if op_tok[1] == '*':
                node = node * right
            elif op_tok[1] == '/':
                if right == 0:
                    raise EvalError(f"division by zero at position {op_tok[2]}")
                node = node / right
            elif op_tok[1] == '//':
                if right == 0:
                    raise EvalError(f"division by zero at position {op_tok[2]}")
                node = math.floor(node / right)
            elif op_tok[1] == '%':
                if right == 0:
                    raise EvalError(f"division by zero at position {op_tok[2]}")
                node = node % right
        return node

    # factor: power
    def factor(self):
        return self.power()

    # power: unary ('**' power)?
    def power(self):
        node = self.unary()
        if self.current()[0] == OP and self.current()[1] == '**':
            op_tok = self.consume(OP)
            right = self.power()  # right-associative
            node = node ** right
        return node

    # unary: (+|-) unary | primary
    def unary(self):
        if self.current()[0] == OP and self.current()[1] in '+-':
            op_tok = self.consume(OP)
            operand = self.unary()
            if op_tok[1] == '+':
                return +operand
            else:
                return -operand
        return self.primary()

    # primary: NUMBER | NAME | function_call | '(' expr ')'
    def primary(self):
        tok = self.current()
        if tok[0] == NUMBER:
            self.consume(NUMBER)
            return int(tok[1]) if '.' not in tok[1] and 'e' not in tok[1] and 'E' not in tok[1] else float(tok[1])
        if tok[0] == NAME:
            name = tok[1]
            pos = tok[2]
            self.consume(NAME)
            if self.current()[0] == LPAREN:
                return self.function_call(name, pos)
            if name in self.variables:
                return self.variables[name]
            raise EvalError(f"unknown name '{name}' at position {pos}")
        if tok[0] == LPAREN:
            self.consume(LPAREN)
            val = self.expr()
            if self.current()[0] != RPAREN:
                raise EvalError(f"unexpected token '{self.current()[1]}' at position {self.current()[2]}")
            self.consume(RPAREN)
            return val
        raise EvalError(f"unexpected token '{tok[1]}' at position {tok[2]}")

    def function_call(self, name: str, pos: int):
        if name not in ('abs', 'min', 'max', 'round'):
            raise EvalError(f"unknown function '{name}' at position {pos}")
        self.consume(LPAREN)
        args = []
        if self.current()[0] != RPAREN:
            while True:
                args.append(self.expr())
                if self.current()[0] == COMMA:
                    self.consume(COMMA)
                else:
                    break
        if self.current()[0] != RPAREN:
            raise EvalError(f"unexpected token '{self.current()[1]}' at position {self.current()[2]}")
        self.consume(RPAREN)
        if name == 'abs':
            if len(args) != 1:
                raise EvalError(f"wrong number of arguments for 'abs' at position {pos}")
            return abs(args[0])
        if name == 'min':
            if len(args) < 1:
                raise EvalError(f"wrong number of arguments for 'min' at position {pos}")
            return min(args)
        if name == 'max':
            if len(args) < 1:
                raise EvalError(f"wrong number of arguments for 'max' at position {pos}")
            return max(args)
        if name == 'round':
            if len(args) == 1:
                return round(args[0])
            if len(args) == 2:
                return round(args[0], int(args[1]))
            raise EvalError(f"wrong number of arguments for 'round' at position {pos}")

def evaluate(expr: str, variables: Optional[Dict[str, Union[int, float]]] = None) -> Union[int, float]:
    tokens = tokenize(expr)
    parser = Parser(tokens, variables)
    return parser.parse()