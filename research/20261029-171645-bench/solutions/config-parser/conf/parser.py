import re
from typing import Dict, List, Tuple, Set, Optional

_key_re = re.compile(r'^[A-Za-z_][A-Za-z0-9_-]*$')
_section_re = re.compile(r'^\s*\[(.*?)\]\s*$')
_inline_comment_re = re.compile(r'(?<=\s)[#;].*')
_interp_re = re.compile(r'\$\$|\$\{([^}]+)\}')

class ConfigError(Exception):
    """Error while parsing or using a configuration."""
    pass


class _Section:
    __slots__ = ('name', 'parent_name', 'keys', 'order')

    def __init__(self, name: str, parent_name: Optional[str] = None):
        self.name = name
        self.parent_name = parent_name
        self.keys: Dict[str, str] = {}          # lower‑cased key -> raw value
        self.order: List[str] = []              # insertion order of keys (original case)


class Config:
    """Parsed configuration."""

    _NO_DEFAULT = object()  # sentinel for missing default

    def __init__(self, sections: Dict[str, _Section], order: List[str]):
        self._sections = sections          # name -> _Section
        self._order = order                # section names in first‑appearance order

    # ---------- public API ----------
    def sections(self) -> List[str]:
        return list(self._order)

    def keys(self, section: str) -> List[str]:
        sec = self._get_section(section)
        merged = self._merged_keys(sec)
        return sorted(merged.keys())

    def get(self, section: str, key: str, default: object = _NO_DEFAULT) -> str:
        # Section may be missing; return default if supplied
        sec = self._sections.get(section)
        if sec is None:
            if default is not self._NO_DEFAULT:
                return default  # type: ignore[return-value]
            raise KeyError(f"Section {section!r} not found")
        merged = self._merged_keys(sec)
        lk = key.lower()
        if lk not in merged:
            if default is not self._NO_DEFAULT:
                return default  # type: ignore[return-value]
            raise KeyError(f"{section!r} has no key {key!r}")
        raw = merged[lk]
        return self._interpolate(raw, sec, set())

    def get_int(self, section: str, key: str, default: object = _NO_DEFAULT) -> int:
        val = self.get(section, key, default)
        return int(val)

    def get_float(self, section: str, key: str, default: object = _NO_DEFAULT) -> float:
        val = self.get(section, key, default)
        return float(val)

    def get_bool(self, section: str, key: str, default: object = _NO_DEFAULT) -> bool:
        val = self.get(section, key, default).lower()
        if val in ('true', 'yes', 'on', '1'):
            return True
        if val in ('false', 'no', 'off', '0'):
            return False
        raise ValueError(f"Invalid boolean value: {val}")

    def get_list(self, section: str, key: str, default: object = _NO_DEFAULT) -> List[str]:
        val = self.get(section, key, default)
        items = [item.strip() for item in val.split(',')]
        return [i for i in items if i]

    # ---------- internal helpers ----------
    def _get_section(self, name: str) -> _Section:
        if name not in self._sections:
            raise KeyError(f"Section {name!r} not found")
        return self._sections[name]

    def _merged_keys(self, sec: _Section) -> Dict[str, str]:
        """Return a dict of all keys visible in this section (including inheritance)."""
        result: Dict[str, str] = {}
        visited: Set[str] = set()
        stack: List[_Section] = []
        cur = sec
        while cur:
            if cur.name in visited:
                # inheritance cycle should have been caught earlier
                break
            visited.add(cur.name)
            # later sections (child) override parents, so we insert parent first
            stack.append(cur)
            cur = self._sections.get(cur.parent_name) if cur.parent_name else None
        # apply from parent to child
        for s in reversed(stack):
            for k, v in s.keys.items():
                result[k] = v
        return result

    def _interpolate(self, value: str, cur_sec: _Section, seen: Set[Tuple[str, str]]) -> str:
        """Resolve ${...} and $$ in a value."""
        def repl(m: re.Match) -> str:
            if m.group(0) == '$$':
                return '$'
            expr = m.group(1)
            if '.' in expr:
                sec_name, key_name = expr.split('.', 1)
                target_sec = self._sections.get(sec_name)
                if not target_sec:
                    raise ConfigError(f"Missing section {sec_name}")
                lk = key_name.lower()
                merged = self._merged_keys(target_sec)
                if lk not in merged:
                    raise ConfigError(f"Missing key {key_name} in section {sec_name}")
                pair = (sec_name, lk)
                if pair in seen:
                    raise ConfigError("Interpolation cycle")
                seen.add(pair)
                resolved = self._interpolate(merged[lk], target_sec, seen)
                seen.remove(pair)
                return resolved
            else:
                lk = expr.lower()
                merged = self._merged_keys(cur_sec)
                if lk not in merged:
                    raise ConfigError(f"Missing key {expr}")
                pair = (cur_sec.name, lk)
                if pair in seen:
                    raise ConfigError("Interpolation cycle")
                seen.add(pair)
                resolved = self._interpolate(merged[lk], cur_sec, seen)
                seen.remove(pair)
                return resolved

        return _interp_re.sub(repl, value)


def parse(text: str) -> Config:
    """Parse INI‑style configuration text."""
    # 1. handle continuations and keep track of first physical line number
    logical_lines: List[Tuple[int, str]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        phys_num = i + 1
        line = lines[i].rstrip('\n')
        # join continuations
        while line.endswith('\\'):
            line = line[:-1]  # remove backslash
            i += 1
            if i >= len(lines):
                break
            next_line = lines[i].lstrip()
            line += next_line
        logical_lines.append((phys_num, line))
        i += 1

    sections: Dict[str, _Section] = {}
    section_order: List[str] = []
    current: Optional[_Section] = None

    for lineno, raw in logical_lines:
        stripped = raw.strip()
        if not stripped or stripped[0] in '#;':
            continue  # blank or comment

        # Section header
        m = _section_re.match(raw)
        if m:
            inner = m.group(1).strip()
            if ':' in inner:
                name_part, parent_part = map(str.strip, inner.split(':', 1))
                name = name_part
                parent = parent_part
            else:
                name = inner
                parent = None
            if name not in sections:
                sec = _Section(name, parent)
                sections[name] = sec
                section_order.append(name)
            else:
                sec = sections[name]
                # merge: later parent overrides earlier? spec says later keys win, parent unchanged.
                if parent is not None:
                    sec.parent_name = parent
            current = sec
            continue

        # Must be a key/value line
        if current is None:
            raise ConfigError(f"line {lineno}")

        if '=' not in raw:
            raise ConfigError(f"line {lineno}")
        key_part, val_part = raw.split('=', 1)
        key = key_part.strip()
        if not _key_re.match(key):
            raise ConfigError(f"line {lineno}")
        lk = key.lower()

        # Process value
        val = val_part.lstrip()
        # Quoted?
        if val.startswith('"'):
            # find closing quote handling escapes
            idx = 1
            out_chars = []
            escaped = False
            while idx < len(val):
                ch = val[idx]
                if escaped:
                    if ch == 'n':
                        out_chars.append('\n')
                    else:
                        out_chars.append(ch)
                    escaped = False
                else:
                    if ch == '\\':
                        escaped = True
                    elif ch == '"':
                        break
                    else:
                        out_chars.append(ch)
                idx += 1
            else:
                raise ConfigError(f"line {lineno}")  # unterminated quote
            value_str = ''.join(out_chars)
            idx += 1  # move past closing quote
            # after closing quote only spaces and optional comment
            rest = val[idx:].strip()
            if rest and not rest.startswith('#') and not rest.startswith(';'):
                raise ConfigError(f"line {lineno}")
        else:
            # unquoted: strip trailing spaces, handle inline comment
            comment_match = _inline_comment_re.search(val)
            if comment_match:
                val = val[:comment_match.start()]
            value_str = val.rstrip()

        # store
        current.keys[lk] = value_str
        if lk not in current.order:
            current.order.append(lk)

    # post‑parse checks: parent existence and cycles
    for sec in sections.values():
        if sec.parent_name and sec.parent_name not in sections:
            raise ConfigError(f"Missing parent section {sec.parent_name}")

    # detect inheritance cycles
    def dfs(name: str, path: Set[str]) -> None:
        if name in path:
            raise ConfigError("inheritance cycle")
        sec = sections[name]
        if sec.parent_name:
            path.add(name)
            dfs(sec.parent_name, path)
            path.remove(name)

    for name in sections:
        dfs(name, set())

    return Config(sections, section_order)