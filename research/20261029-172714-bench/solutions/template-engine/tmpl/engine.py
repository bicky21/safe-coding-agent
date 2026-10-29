import re
import html

class TemplateError(Exception):
    """Exception raised for errors in the template."""
    pass

# Helper functions for filters
def _filter_upper(value):
    return str(value).upper()

def _filter_lower(value):
    return str(value).lower()

def _filter_title(value):
    return str(value).title()

def _filter_length(value):
    try:
        return len(value)
    except Exception:
        return 0

def _filter_join(value, sep):
    try:
        return sep.join(str(item) for item in value)
    except Exception:
        return ""

def _filter_default(value, text):
    if value is None or value == "" or value == "undefined":
        return text
    return value

def _filter_safe(value):
    return value

FILTERS = {
    "upper": lambda v: _filter_upper(v),
    "lower": lambda v: _filter_lower(v),
    "title": lambda v: _filter_title(v),
    "length": lambda v: _filter_length(v),
    "join": lambda v, sep: _filter_join(v, sep),
    "default": lambda v, text: _filter_default(v, text),
    "safe": lambda v: _filter_safe(v),
}

# Token types
TOKEN_TEXT = "text"
TOKEN_VAR = "var"
TOKEN_BLOCK = "block"
TOKEN_COMMENT = "comment"

# Regex patterns
VAR_PATTERN = re.compile(r"\{\{\s*(-)?\s*(.*?)\s*(-)?\s*\}\}")
BLOCK_PATTERN = re.compile(r"\{\%\s*(-)?\s*(.*?)\s*(-)?\s*\%\}")
COMMENT_PATTERN = re.compile(r"\{#\s*(-)?\s*(.*?)\s*(-)?\s*#\}")

# Whitespace stripping flags
def strip_left(s):
    return s.lstrip()

def strip_right(s):
    return s.rstrip()

class Token:
    def __init__(self, typ, content, line):
        self.typ = typ
        self.content = content
        self.line = line

def tokenize(template):
    tokens = []
    pos = 0
    line = 1
    while pos < len(template):
        # Check for comment
        m = COMMENT_PATTERN.search(template, pos)
        m_var = VAR_PATTERN.search(template, pos)
        m_block = BLOCK_PATTERN.search(template, pos)
        # Find the earliest
        candidates = [(m, TOKEN_COMMENT), (m_var, TOKEN_VAR), (m_block, TOKEN_BLOCK)]
        candidates = [(m, t) for m, t in candidates if m]
        if not candidates:
            # Remaining text
            tokens.append(Token(TOKEN_TEXT, template[pos:], line))
            break
        m, ttype = min(candidates, key=lambda x: x[0].start())
        start, end = m.span()
        if start > pos:
            tokens.append(Token(TOKEN_TEXT, template[pos:start], line))
        # Handle whitespace stripping
        left_strip = bool(m.group(1))
        right_strip = bool(m.group(3))
        content = m.group(2)
        if left_strip:
            content = strip_left(content)
        if right_strip:
            content = strip_right(content)
        tokens.append(Token(ttype, content, line + template[pos:start].count("\n")))
        pos = end
    return tokens

def resolve_name(name_parts, context):
    val = "undefined"
    for part in name_parts:
        if isinstance(val, dict):
            val = val.get(part, "undefined")
        else:
            try:
                val = getattr(val, part)
            except Exception:
                val = "undefined"
        if val == "undefined":
            break
    return val

def apply_filters(value, filters, line):
    for f in filters:
        if f[0] == "safe":
            # safe filter just marks value as safe
            value = _filter_safe(value)
            continue
        if f[0] not in FILTERS:
            raise TemplateError(f"Unknown filter '{f[0]}' at line {line}")
        try:
            if f[1] is None:
                value = FILTERS[f[0]](value)
            else:
                value = FILTERS[f[0]](value, f[1])
        except Exception:
            value = ""
    return value

def eval_expr(expr, context, line):
    # expr is something like "user.name|upper|default:'Guest'"
    parts = [p.strip() for p in expr.split("|")]
    name_part = parts[0]
    filters = []
    for f in parts[1:]:
        if ":" in f:
            fname, farg = f.split(":", 1)
            farg = farg.strip()
            if farg.startswith("'") and farg.endswith("'"):
                farg = farg[1:-1]
            elif farg.startswith('"') and farg.endswith('"'):
                farg = farg[1:-1]
            else:
                # treat as literal
                pass
            filters.append((fname.strip(), farg))
        else:
            filters.append((f.strip(), None))
    name_parts = [p.strip() for p in name_part.split(".")]
    val = resolve_name(name_parts, context)
    if val == "undefined":
        val = ""
    val = apply_filters(val, filters, line)
    # final conversion
    if val is None:
        return ""
    if isinstance(val, bool):
        return "true" if val else "false"
    return str(val)

def render(template, context):
    tokens = tokenize(template)
    output = []
    # Stack for blocks
    stack = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.typ == TOKEN_TEXT:
            output.append(tok.content)
        elif tok.typ == TOKEN_COMMENT:
            pass  # ignore
        elif tok.typ == TOKEN_VAR:
            try:
                val = eval_expr(tok.content, context, tok.line)
                # Escape unless safe
                if not any(f[0]=="safe" for f in [("safe",None)]):
                    val = html.escape(val)
                output.append(val)
            except TemplateError as e:
                raise TemplateError(f"{e} at line {tok.line}") from None
        elif tok.typ == TOKEN_BLOCK:
            words = tok.content.split()
            if not words:
                raise TemplateError(f"Empty block tag at line {tok.line}")
            tag = words[0]
            if tag == "if":
                cond = " ".join(words[1:])
                cond_val = eval_expr(cond, context, tok.line)
                cond_bool = bool(cond_val)
                stack.append({"type":"if","cond":cond_bool,"line":tok.line,"else":False,"elif":False})
            elif tag == "elif":
                if not stack or stack[-1]["type"]!="if":
                    raise TemplateError(f"elif without if at line {tok.line}")
                if stack[-1]["else"]:
                    raise TemplateError(f"elif after else at line {tok.line}")
                cond = " ".join(words[1:])
                cond_val = eval_expr(cond, context, tok.line)
                stack[-1]["cond"] = bool(cond_val)
                stack[-1]["elif"]=True
            elif tag == "else":
                if not stack or stack[-1]["type"]!="if":
                    raise TemplateError(f"else without if at line {tok.line}")
                stack[-1]["else"]=True
            elif tag == "endif":
                if not stack or stack[-1]["type"]!="if":
                    raise TemplateError(f"endif without if at line {tok.line}")
                stack.pop()
            elif tag == "for":
                if len(words)!=4 or words[2]!="in":
                    raise TemplateError(f"Invalid for syntax at line {tok.line}")
                var_name = words[1]
                iterable_expr = words[3]
                iterable = eval_expr(iterable_expr, context, tok.line)
                if iterable is None or iterable=="" or iterable=="undefined":
                    iterable = []
                if not hasattr(iterable, "__iter__"):
                    iterable = []
                loop_context = {"loop": {"index":1,"first":True,"last":False,"length":len(iterable)}}
                stack.append({"type":"for","var":var_name,"iterable":iterable,"index":0,"loop_context":loop_context,"line":tok.line,"else":False})
            elif tag == "else":
                if not stack or stack[-1]["type"]!="for":
                    raise TemplateError(f"else without for at line {tok.line}")
                stack[-1]["else"]=True
            elif tag == "endfor":
                if not stack or stack[-1]["type"]!="for":
                    raise TemplateError(f"endfor without for at line {tok.line}")
                stack.pop()
            else:
                raise TemplateError(f"Unknown tag '{tag}' at line {tok.line}")
        i+=1
    if stack:
        raise TemplateError(f"Unclosed block starting at line {stack[-1]['line']}")
    return "".join(output)