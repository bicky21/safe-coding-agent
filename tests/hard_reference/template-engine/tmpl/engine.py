"""Reference solution for the template-engine task (used only to check the task's tests)."""

import re


class TemplateError(Exception):
    pass


_UNDEF = object()
_OPEN = re.compile(r"\{\{|\{%|\{#")
_CLOSE = {"{{": "}}", "{%": "%}", "{#": "#}"}
_NAME = r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*"
_EXPR = re.compile(r"^(" + _NAME + r")((?:\s*\|\s*[A-Za-z_]\w*(?:\s*:\s*\"[^\"]*\")?)*)$")
_FILTER = re.compile(r"\|\s*([A-Za-z_]\w*)(?:\s*:\s*\"([^\"]*)\")?")
_ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}


def _tokens(src):
    out, pos, strip_next = [], 0, False
    while True:
        m = _OPEN.search(src, pos)
        text = src[pos:m.start()] if m else src[pos:]
        if strip_next:
            text = text.lstrip()
        if text:
            out.append(("text", text, 0))
        if not m:
            return out
        kind = m.group()
        line = src.count("\n", 0, m.start()) + 1
        end = src.find(_CLOSE[kind], m.end())
        if end == -1:
            raise TemplateError(f"unclosed {kind} at line {line}")
        inner = src[m.end():end]
        pos = end + 2
        strip_next = False
        if kind == "{#":
            continue
        if inner.startswith("-"):
            inner = inner[1:]
            if out and out[-1][0] == "text":
                stripped = out[-1][1].rstrip()
                out[-1] = ("text", stripped, 0)
                if not stripped:
                    out.pop()
        if inner.endswith("-"):
            inner = inner[:-1]
            strip_next = True
        out.append(("var" if kind == "{{" else "tag", inner.strip(), line))


def _parse(tokens):
    root = []
    stack = [("root", root, None, 0)]   # (kind, body list, node, line)
    for kind, val, line in tokens:
        body = stack[-1][1]
        if kind == "text":
            body.append(("text", val))
        elif kind == "var":
            m = _EXPR.match(val)
            if not m:
                raise TemplateError(f"invalid expression {val!r} at line {line}")
            filters = [(f, a) for f, a in _FILTER.findall(m.group(2))]
            for f, _ in filters:
                if f not in ("upper", "lower", "title", "length", "join", "default", "safe"):
                    raise TemplateError(f"unknown filter {f!r} at line {line}")
            body.append(("var", m.group(1), filters))
        else:
            word = val.split()[0] if val.split() else ""
            if word == "if":
                cond = _cond(val[2:].strip(), line)
                node = {"type": "if", "branches": [(cond, [])], "else": None}
                body.append(("block", node))
                stack.append(("if", node["branches"][0][1], node, line))
            elif word == "elif":
                top = stack[-1]
                if top[0] != "if" or top[2]["else"] is not None:
                    raise TemplateError(f"unexpected 'elif' at line {line}")
                cond = _cond(val[4:].strip(), line)
                top[2]["branches"].append((cond, []))
                stack[-1] = ("if", top[2]["branches"][-1][1], top[2], top[3])
            elif word == "else" and val == "else":
                top = stack[-1]
                if top[0] not in ("if", "for") or top[2]["else"] is not None:
                    raise TemplateError(f"unexpected 'else' at line {line}")
                top[2]["else"] = []
                stack[-1] = (top[0], top[2]["else"], top[2], top[3])
            elif word == "endif" and val == "endif":
                if stack[-1][0] != "if":
                    raise TemplateError(f"unexpected 'endif' at line {line}")
                stack.pop()
            elif word == "for":
                m = re.match(r"^for\s+([A-Za-z_]\w*)\s+in\s+(" + _NAME + r")$", val)
                if not m:
                    raise TemplateError(f"invalid for tag at line {line}")
                node = {"type": "for", "var": m.group(1), "items": m.group(2), "body": [], "else": None}
                body.append(("block", node))
                stack.append(("for", node["body"], node, line))
            elif word == "endfor" and val == "endfor":
                if stack[-1][0] != "for":
                    raise TemplateError(f"unexpected 'endfor' at line {line}")
                stack.pop()
            else:
                raise TemplateError(f"unknown tag {val!r} at line {line}")
    if len(stack) > 1:
        kind, _, _, line = stack[-1]
        raise TemplateError(f"unclosed '{kind}' at line {line}")
    return root


def _cond(text, line):
    neg = False
    if text.startswith("not "):
        neg, text = True, text[4:].strip()
    if not re.fullmatch(_NAME, text):
        raise TemplateError(f"invalid condition at line {line}")
    return neg, text


def _lookup(name, scopes):
    parts = name.split(".")
    value = _UNDEF
    for scope in reversed(scopes):
        if isinstance(scope, dict) and parts[0] in scope:
            value = scope[parts[0]]
            break
    if value is _UNDEF:
        return _UNDEF
    for p in parts[1:]:
        if isinstance(value, dict) and p in value:
            value = value[p]
        elif not isinstance(value, dict) and hasattr(value, p):
            value = getattr(value, p)
        else:
            return _UNDEF
    return value


def _render_var(name, filters, scopes):
    value = _lookup(name, scopes)
    safe = False
    for f, arg in filters:
        if f == "default":
            if value is _UNDEF or value is None or value == "":
                value = arg
            continue
        if value is _UNDEF:
            value = ""
        if f == "upper":
            value = str(value).upper()
        elif f == "lower":
            value = str(value).lower()
        elif f == "title":
            value = str(value).title()
        elif f == "length":
            value = len(value)
        elif f == "join":
            value = arg.join(str(x) for x in value)
        elif f == "safe":
            safe = True
    if value is _UNDEF or value is None:
        text = ""
    elif value is True or value is False:
        text = "true" if value else "false"
    else:
        text = str(value)
    return text if safe else "".join(_ESC.get(c, c) for c in text)


def _render(nodes, scopes, out):
    for node in nodes:
        if node[0] == "text":
            out.append(node[1])
        elif node[0] == "var":
            out.append(_render_var(node[1], node[2], scopes))
        else:
            block = node[1]
            if block["type"] == "if":
                for (neg, name), body in block["branches"]:
                    value = _lookup(name, scopes)
                    truth = False if value is _UNDEF else bool(value)
                    if truth != neg:
                        _render(body, scopes, out)
                        break
                else:
                    if block["else"] is not None:
                        _render(block["else"], scopes, out)
            else:
                items = _lookup(block["items"], scopes)
                items = [] if items is _UNDEF or items is None else list(items)
                if not items:
                    if block["else"] is not None:
                        _render(block["else"], scopes, out)
                    continue
                n = len(items)
                for i, item in enumerate(items):
                    loop = {"index": i + 1, "first": i == 0, "last": i == n - 1, "length": n}
                    _render(block["body"], scopes + [{block["var"]: item, "loop": loop}], out)


def render(template, context):
    out = []
    _render(_parse(_tokens(template)), [dict(context)], out)
    return "".join(out)
