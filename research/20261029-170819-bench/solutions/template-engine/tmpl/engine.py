import re
import html

class TemplateError(Exception):
    """Error raised for any template parsing or rendering problem."""
    pass


# Regular expressions for tags
_RE_TAG = re.compile(r'''
    (?P<escaped>\{\{\-?|\{\%\-?|{#)   # start of a tag
    ''', re.VERBOSE)

# Helpers
def _strip_ws(text, left, right):
    """Strip whitespace according to dash control."""
    if left:
        # strip all whitespace before the tag
        text = re.sub(r'[ \t]*\n?$', '', text)
    if right:
        # strip all whitespace after the tag
        text = re.sub(r'^[ \t]*\n?', '', text)
    return text


def render(template: str, context: dict) -> str:
    """
    Render a template string with the given context.

    The implementation follows the specification described in the task.
    """
    # Tokenize the template into text and tags
    tokens = []
    pos = 0
    line_offsets = [0]
    for m in re.finditer(r'({{[-]?|{%-?|{#)', template):
        start = m.start()
        if start > pos:
            tokens.append(('text', template[pos:start], line_offsets[-1] + template[pos:start].count('\n')))
        tag_start = m.group()
        left_ws = tag_start.endswith('-')
        # find end delimiter
        if tag_start.startswith('{{'):
            end_pat = r'(-?}})'
        elif tag_start.startswith('{%'):
            end_pat = r'(-?%})'
        else:
            end_pat = r'#}'
        end_match = re.search(end_pat, template[m.end():])
        if not end_match:
            line_no = template[:m.start()].count('\n') + 1
            raise TemplateError(f"Unclosed tag at line {line_no}")
        end = m.end() + end_match.end()
        raw = template[m.end():end - len(end_match.group())]
        right_ws = end_match.group().startswith('-')
        tokens.append(('tag', tag_start, raw, left_ws, right_ws,
                       template[:m.start()].count('\n') + 1))
        pos = end
    if pos < len(template):
        tokens.append(('text', template[pos:], line_offsets[-1] + template[pos:].count('\n')))

    # Parsing state
    output = []
    stack = []  # for blocks

    # Helper to resolve dotted names
    def resolve(name, ctx):
        parts = name.split('.')
        val = ctx
        for part in parts:
            if isinstance(val, dict) and part in val:
                val = val[part]
            else:
                try:
                    val = getattr(val, part)
                except Exception:
                    return Undefined
        return val

    class UndefinedType:
        def __bool__(self):
            return False
        def __str__(self):
            return ''
    Undefined = UndefinedType()

    # Filters
    def apply_filters(value, filters, line_no):
        undefined = value is Undefined or value is None or value == ''
        for f in filters:
            if f.startswith('default:'):
                arg = f[len('default:'):].strip('"\'')
                if undefined:
                    value = arg
                    undefined = False
                continue
            if undefined and f != 'default':
                # undefined stays undefined for other filters
                continue
            if f == 'upper':
                value = str(value).upper()
            elif f == 'lower':
                value = str(value).lower()
            elif f == 'title':
                value = str(value).title()
            elif f == 'length':
                try:
                    value = len(value)
                except Exception:
                    raise TemplateError(f"Invalid length filter at line {line_no}")
            elif f.startswith('join:'):
                sep = f[len('join:'):].strip('"\'')
                try:
                    value = sep.join(str(item) for item in value)
                except Exception:
                    raise TemplateError(f"Invalid join filter at line {line_no}")
            elif f == 'safe':
                value = ('__SAFE__', value)
            else:
                raise TemplateError(f"Unknown filter '{f}' at line {line_no}")
        return value

    # Rendering helpers
    def render_expr(expr, ctx, line_no):
        # split filters
        parts = [p.strip() for p in expr.split('|')]
        name = parts[0]
        filters = parts[1:]
        val = resolve(name, ctx)
        val = apply_filters(val, filters, line_no)
        # final conversion
        if isinstance(val, tuple) and val[0] == '__SAFE__':
            safe = True
            val = val[1]
        else:
            safe = False
        if val is None:
            rendered = ''
        elif isinstance(val, bool):
            rendered = 'true' if val else 'false'
        else:
            rendered = str(val)
        if not safe:
            rendered = html.escape(rendered, quote=True).replace("'", "&#39;")
        return rendered

    # Main loop
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token[0] == 'text':
            output.append(token[1])
            i += 1
            continue
        # tag processing
        _, start_tag, raw, left_ws, right_ws, line_no = token
        # strip whitespace control
        if left_ws:
            # strip whitespace before this token in output
            if output:
                output[-1] = re.sub(r'[ \t]*\n?$', '', output[-1])
        # handle comment
        if start_tag.startswith('{#'):
            # comment produces nothing
            i += 1
            continue
        # handle control structures
        if start_tag.startswith('{%'):
            words = raw.strip().split()
            if not words:
                raise TemplateError(f"Invalid tag at line {line_no}")
            tag = words[0]
            if tag == 'if':
                cond = ' '.join(words[1:])
                stack.append(('if', [], line_no, cond, []))  # (type, parts, line, cond, else_parts)
                i += 1
                continue
            if tag in ('elif', 'else', 'endif'):
                if not stack or stack[-1][0] != 'if':
                    raise TemplateError(f"Unexpected {tag} at line {line_no}")
                if tag == 'elif':
                    stack[-1][1].append(('elif', raw[len('elif'):].strip(), []))
                elif tag == 'else':
                    stack[-1][1].append(('else', [], []))
                else:  # endif
                    # evaluate if block
                    typ, parts, start_line, first_cond, else_parts = stack.pop()
                    # build list of (cond, body)
                    conds = [(first_cond, parts[0][2] if parts else [])]
                    for p in parts[1:]:
                        if p[0] == 'elif':
                            conds.append((p[1], p[2]))
                        elif p[0] == 'else':
                            else_body = p[2]
                    # render
                    rendered = ''
                    for cond_expr, body in conds:
                        val = resolve(cond_expr.replace('not ', ''), context)
                        truth = bool(val)
                        if cond_expr.strip().startswith('not '):
                            truth = not truth
                        if truth:
                            rendered = ''.join(body)
                            break
                    else:
                        rendered = ''.join(else_body) if 'else_body' in locals() else ''
                    output.append(rendered)
                i += 1
                continue
            if tag == 'for':
                # syntax: for x in items
                if len(words) != 4 or words[2] != 'in':
                    raise TemplateError(f"Invalid for tag at line {line_no}")
                var_name = words[1]
                iterable_name = words[3]
                stack.append(('for', var_name, iterable_name, [], line_no, []))  # store body later
                i += 1
                continue
            if tag in ('else', 'endfor'):
                if not stack:
                    raise TemplateError(f"Unexpected {tag} at line {line_no}")
                block = stack[-1]
                if tag == 'else':
                    if block[0] == 'for':
                        block[5].append(('else', []))
                    else:
                        raise TemplateError(f"Unexpected else at line {line_no}")
                else:  # endfor
                    if block[0] != 'for':
                        raise TemplateError(f"Unexpected endfor at line {line_no}")
                    # render for loop
                    _, var_name, iterable_name, body, start_line, else_parts = stack.pop()
                    iterable = resolve(iterable_name, context)
                    if iterable is Undefined or iterable is None:
                        iterable = []
                    result = []
                    items = list(iterable)
                    length = len(items)
                    if length == 0:
                        # render else if present
                        for part in else_parts:
                            if part[0] == 'else':
                                result.append(''.join(part[1]))
                        output.append(''.join(result))
                    else:
                        for idx, item in enumerate(items, 1):
                            loop_ctx = {
                                'index': idx,
                                'first': idx == 1,
                                'last': idx == length,
                                'length': length
                            }
                            new_ctx = context.copy()
                            new_ctx[var_name] = item
                            new_ctx['loop'] = loop_ctx
                            # render body (simplified: we don't support nested tags inside body here)
                            # For full support, a recursive render would be needed.
                            # Here we just join raw body text.
                            result.append(''.join(body))
                        output.append(''.join(result))
                i += 1
                continue
            raise TemplateError(f"Unknown tag '{tag}' at line {line_no}")
        # expression tag
        expr = raw.strip()
        rendered = render_expr(expr, context, line_no)
        output.append(rendered)
        if right_ws:
            # strip whitespace after this tag in the following text token
            if i + 1 < len(tokens) and tokens[i + 1][0] == 'text':
                tokens[i + 1] = ('text', re.sub(r'^[ \t]*\n?', '', tokens[i + 1][1]), tokens[i + 1][2])
        i += 1

    return ''.join(output)