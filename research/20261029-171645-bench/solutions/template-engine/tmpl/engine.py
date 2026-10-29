import re
import html
from typing import Any, List, Tuple, Dict

class TemplateError(Exception):
    """Error raised for any template parsing or rendering problem."""
    pass


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def _escape(value: str) -> str:
    """HTML‑escape a string."""
    return (value.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;")
                 .replace("'", "&#39;"))


def _is_undefined(val: Any) -> bool:
    return isinstance(val, Undefined)


class Undefined:
    """Sentinel for undefined values."""
    def __repr__(self):
        return "undefined"


UNDEFINED = Undefined()


def _resolve(name: str, ctx: Dict[str, Any]) -> Any:
    """Resolve a dotted name in the given context."""
    parts = name.split(".")
    cur = ctx
    for part in parts:
        if isinstance(cur, dict):
            cur = cur.get(part, UNDEFINED)
        else:
            cur = getattr(cur, part, UNDEFINED)
        if _is_undefined(cur):
            return UNDEFINED
    return cur


def _apply_filter(value: Any, filt: str, arg: str, line_no: int) -> Any:
    """Apply a single filter to a value."""
    # undefined handling: treat as "" for all except default
    if _is_undefined(value):
        if filt == "default":
            return arg
        value = ""

    # string case filters
    if filt in ("upper", "lower", "title"):
        s = str(value)
        if filt == "upper":
            return s.upper()
        if filt == "lower":
            return s.lower()
        if filt == "title":
            return s.title()

    if filt == "length":
        try:
            return len(value)
        except Exception:
            raise TemplateError(f"line {line_no}: cannot get length of {value!r}")

    if filt == "join":
        sep = arg
        try:
            return sep.join(str(item) for item in value)
        except Exception:
            raise TemplateError(f"line {line_no}: cannot join {value!r}")

    if filt == "default":
        return value if value not in (None, "") else arg

    raise TemplateError(f"line {line_no}: unknown filter '{filt}'")


def _finalise(value: Any) -> Tuple[str, bool]:
    """Convert the final value to a string and tell whether it is safe."""
    if _is_undefined(value) or value is None:
        return "", False
    if isinstance(value, bool):
        return "true" if value else "false", False
    return str(value), False


# ----------------------------------------------------------------------
# Node definitions
# ----------------------------------------------------------------------
class Node:
    def render(self, ctx: Dict[str, Any]) -> str:
        raise NotImplementedError


class TextNode(Node):
    def __init__(self, text: str):
        self.text = text

    def render(self, ctx: Dict[str, Any]) -> str:
        return self.text


class ExprNode(Node):
    def __init__(self, expr: str, line_no: int, strip_left: bool, strip_right: bool):
        self.expr = expr.strip()
        self.line_no = line_no
        self.strip_left = strip_left
        self.strip_right = strip_right

    def _split_filters(self, expr: str) -> List[Tuple[str, str]]:
        """Split expression into name and list of (filter, arg). Handles quoted args."""
        parts = []
        i = 0
        n = len(expr)
        current = ""
        in_quote = False
        quote_char = ''
        while i < n:
            c = expr[i]
            if c in ('"', "'"):
                if not in_quote:
                    in_quote = True
                    quote_char = c
                elif quote_char == c:
                    in_quote = False
                current += c
            elif c == "|" and not in_quote:
                parts.append(current)
                current = ""
            else:
                current += c
            i += 1
        parts.append(current)

        name = parts[0].strip()
        filters = []
        for f in parts[1:]:
            f = f.strip()
            if ":" in f:
                filt, arg = f.split(":", 1)
                arg = arg.strip().strip('"\'')
            else:
                filt, arg = f, ""
            filters.append((filt.strip(), arg))
        return name, filters

    def render(self, ctx: Dict[str, Any]) -> str:
        name, filters = self._split_filters(self.expr)
        if not name:
            raise TemplateError(f"line {self.line_no}: empty expression")
        value = _resolve(name, ctx)

        safe = False
        for filt, arg in filters:
            if filt == "safe":
                safe = True
                continue
            value = _apply_filter(value, filt, arg, self.line_no)

        final, _ = _finalise(value)
        if not safe:
            final = _escape(final)
        return final


class IfNode(Node):
    def __init__(self, line_no: int, strip_left: bool = False, strip_right: bool = False):
        self.line_no = line_no
        self.strip_left = strip_left
        self.strip_right = strip_right
        self.branches: List[Tuple[str, List[Node]]] = []  # (condition, nodes)
        self.else_branch: List[Node] = []

    def render(self, ctx: Dict[str, Any]) -> str:
        for cond, nodes in self.branches:
            if _eval_cond(cond, ctx):
                return "".join(n.render(ctx) for n in nodes)
        return "".join(n.render(ctx) for n in self.else_branch)


class ForNode(Node):
    def __init__(self, var_name: str, iterable_expr: str, line_no: int,
                 strip_left: bool = False, strip_right: bool = False):
        self.var_name = var_name
        self.iterable_expr = iterable_expr
        self.line_no = line_no
        self.strip_left = strip_left
        self.strip_right = strip_right
        self.body: List[Node] = []
        self.else_body: List[Node] = []

    def render(self, ctx: Dict[str, Any]) -> str:
        iterable = _resolve(self.iterable_expr, ctx)
        if _is_undefined(iterable) or iterable is None:
            iterable = []
        try:
            seq = list(iterable)
        except Exception:
            raise TemplateError(f"line {self.line_no}: cannot iterate over {iterable!r}")

        if not seq:
            return "".join(n.render(ctx) for n in self.else_body)

        out = []
        length = len(seq)
        for idx, item in enumerate(seq, start=1):
            inner = ctx.copy()
            inner[self.var_name] = item
            inner["loop"] = {
                "index": idx,
                "first": idx == 1,
                "last": idx == length,
                "length": length,
            }
            out.append("".join(n.render(inner) for n in self.body))
        return "".join(out)


# ----------------------------------------------------------------------
# Condition evaluation
# ----------------------------------------------------------------------
def _eval_cond(cond: str, ctx: Dict[str, Any]) -> bool:
    cond = cond.strip()
    neg = False
    if cond.startswith("not "):
        neg = True
        cond = cond[4:].strip()
    val = _resolve(cond, ctx)
    truth = bool(val) and not _is_undefined(val)
    return not truth if neg else truth


# ----------------------------------------------------------------------
# Parser
# ----------------------------------------------------------------------
TOKEN_RE = re.compile(r"({{[-]?|{%-?|{#)(.*?)(-?%}|-?}}|#})", re.DOTALL)


def _parse(template: str) -> List[Node]:
    pos = 0
    line_no = 1
    stack: List[Tuple[str, Any]] = []  # (type, node)
    root: List[Node] = []
    current = root

    for m in TOKEN_RE.finditer(template):
        start, end = m.span()
        before = template[pos:start]
        if before:
            current.append(TextNode(before))
            line_no += before.count("\n")

        tag_start, inner, tag_end = m.groups()
        strip_left = tag_start.endswith("-")
        strip_right = tag_end.startswith("-")
        tag_content = inner.strip()
        tag_line = line_no
        line_no += inner.count("\n")

        if tag_start.startswith("{#"):
            pass

        elif tag_start.startswith("{{"):
            node = ExprNode(tag_content, tag_line, strip_left, strip_right)
            current.append(node)

        elif tag_start.startswith("{%"):
            parts = tag_content.split()
            if not parts:
                raise TemplateError(f"line {tag_line}: empty tag")
            keyword = parts[0]

            if keyword == "if":
                node = IfNode(tag_line, strip_left, strip_right)
                node.branches.append(( " ".join(parts[1:]), [] ))
                current.append(node)
                stack.append(("if", node))
                current = node.branches[-1][1]

            elif keyword == "elif":
                if not stack or stack[-1][0] != "if":
                    raise TemplateError(f"line {tag_line}: unexpected elif")
                node: IfNode = stack[-1][1]
                node.branches.append(( " ".join(parts[1:]), [] ))
                current = node.branches[-1][1]

            elif keyword == "else":
                if not stack or stack[-1][0] not in ("if", "for"):
                    raise TemplateError(f"line {tag_line}: unexpected else")
                typ, node = stack[-1]
                if typ == "if":
                    node.else_branch = []
                    current = node.else_branch
                else:
                    node.else_body = []
                    current = node.else_body

            elif keyword == "endif":
                if not stack or stack[-1][0] != "if":
                    raise TemplateError(f"line {tag_line}: unexpected endif")
                stack.pop()
                current = root if not stack else _current_body(stack)

            elif keyword == "for":
                if len(parts) != 4 or parts[2] != "in":
                    raise TemplateError(f"line {tag_line}: invalid for syntax")
                var_name = parts[1]
                iterable = parts[3]
                node = ForNode(var_name, iterable, tag_line, strip_left, strip_right)
                current.append(node)
                stack.append(("for", node))
                current = node.body

            elif keyword == "endfor":
                if not stack or stack[-1][0] != "for":
                    raise TemplateError(f"line {tag_line}: unexpected endfor")
                stack.pop()
                current = root if not stack else _current_body(stack)

            else:
                raise TemplateError(f"line {tag_line}: unknown tag '{keyword}'")
        else:
            raise TemplateError(f"line {tag_line}: unknown delimiter")

        pos = end

    after = template[pos:]
    if after:
        current.append(TextNode(after))

    if stack:
        typ, node = stack[-1]
        raise TemplateError(f"line {node.line_no}: unclosed {typ}")

    _apply_whitespace_control(root)
    return root


def _current_body(stack: List[Tuple[str, Any]]) -> List[Node]:
    typ, node = stack[-1]
    if typ == "if":
        if node.branches:
            return node.branches[-1][1]
        return node.else_branch
    if typ == "for":
        return node.body
    return []


def _apply_whitespace_control(nodes: List[Node]) -> None:
    i = 0
    while i < len(nodes):
        node = nodes[i]
        if isinstance(node, (ExprNode, IfNode, ForNode)):
            if node.strip_left and i > 0 and isinstance(nodes[i-1], TextNode):
                nodes[i-1].text = re.sub(r"[ \t\r\f\v]*\n?$", "", nodes[i-1].text)
            if node.strip_right and i + 1 < len(nodes) and isinstance(nodes[i+1], TextNode):
                nodes[i+1].text = re.sub(r"^[ \t\r\f\v]*\n?", "", nodes[i+1].text)
        if isinstance(node, IfNode):
            for _, child in node.branches:
                _apply_whitespace_control(child)
            _apply_whitespace_control(node.else_branch)
        if isinstance(node, ForNode):
            _apply_whitespace_control(node.body)
            _apply_whitespace_control(node.else_body)
        i += 1


def render(template: str, context: dict) -> str:
    """
    Render *template* using *context*.
    """
    try:
        nodes = _parse(template)
        return "".join(node.render(context) for node in nodes)
    except TemplateError:
        raise
    except Exception as exc:
        raise TemplateError(str(exc))