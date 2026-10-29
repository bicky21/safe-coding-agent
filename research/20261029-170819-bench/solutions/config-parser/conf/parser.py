import re
from typing import Dict, List, Tuple, Set, Optional

# ----------------------------------------------------------------------
# Exceptions
# ----------------------------------------------------------------------
class ConfigError(Exception):
    """Error while parsing or accessing configuration."""
    pass


# ----------------------------------------------------------------------
# Helper data structures
# ----------------------------------------------------------------------
_KEY_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_-]*$')
_SECTION_RE = re.compile(r'^\s*\[([^\]]+)\]\s*$')
_INHERIT_RE = re.compile(r'^\s*([^\s:]+)\s*:\s*([^\s:]+)\s*$')
_QUOTE_ESCAPES = {
    '\\': '\\',
    '"': '"',
    'n': '\n',
}


# ----------------------------------------------------------------------
# Config object
# ----------------------------------------------------------------------
class Config:
    """
    Holds parsed configuration data.
    """

    def __init__(self,
                 sections: Dict[str, Dict[str, str]],
                 parents: Dict[str, Optional[str]],
                 order: List[str]):
        self._sections_raw = sections          # raw key->value (no inheritance)
        self._parents = parents                # section -> parent name or None
        self._order = order                    # order of first appearance
        self._merged_cache: Dict[str, Dict[str, str]] = {}

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------
    def _merged(self, section: str) -> Dict[str, str]:
        """Return a dict of keys->values for *section* including inheritance."""
        if section in self._merged_cache:
            return self._merged_cache[section]

        if section not in self._sections_raw:
            raise KeyError(section)

        parent = self._parents.get(section)
        merged: Dict[str, str] = {}
        if parent:
            # detect cycles
            visited = set()
            cur = section
            while cur:
                if cur in visited:
                    raise ConfigError(f"inheritance cycle involving {cur}")
                visited.add(cur)
                cur = self._parents.get(cur)
            # recursive merge
            merged.update(self._merged(parent))
        merged.update(self._sections_raw[section])
        self._merged_cache[section] = merged
        return merged

    def _interpolate(self,
                     value: str,
                     cur_section: str,
                     visited: Set[Tuple[str, str]]) -> str:
        """Perform ${...} interpolation on *value*."""
        def repl(m: re.Match) -> str:
            expr = m.group(1)
            if expr == '':
                # $$ case handled before regex
                return '$'
            if '.' in expr:
                sec, key = expr.split('.', 1)
                sec = sec.strip()
                key = key.strip().lower()
                target_section = sec
            else:
                sec = cur_section
                key = expr.strip().lower()
                target_section = sec

            pair = (target_section, key)
            if pair in visited:
                raise ConfigError("interpolation cycle")
            visited.add(pair)

            try:
                raw = self.get(target_section, key)
            except KeyError:
                raise ConfigError(f"missing reference {expr}")

            # recurse
            result = self._interpolate(raw, target_section, visited)
            visited.remove(pair)
            return result

        # $$ -> placeholder to avoid being caught
        placeholder = "\0"
        value = value.replace('$$', placeholder)

        pattern = re.compile(r'\$\{([^}]+)\}')
        result = pattern.sub(repl, value)

        result = result.replace(placeholder, '$')
        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get(self, section: str, key: str, default: Optional[str] = None) -> str:
        sec = section
        if sec not in self._sections_raw:
            if default is not None:
                return default
            raise KeyError(section)
        merged = self._merged(sec)
        k = key.lower()
        if k not in merged:
            if default is not None:
                return default
            raise KeyError(key)
        raw = merged[k]
        # interpolation
        try:
            return self._interpolate(raw, sec, set())
        except ConfigError as e:
            raise ConfigError(str(e))

    def get_int(self, section: str, key: str) -> int:
        return int(self.get(section, key))

    def get_float(self, section: str, key: str) -> float:
        return float(self.get(section, key))

    def get_bool(self, section: str, key: str) -> bool:
        val = self.get(section, key).lower()
        if val in ('true', 'yes', 'on', '1'):
            return True
        if val in ('false', 'no', 'off', '0'):
            return False
        raise ValueError(f"invalid boolean value: {val}")

    def get_list(self, section: str, key: str) -> List[str]:
        raw = self.get(section, key)
        items = [item.strip() for item in raw.split(',')]
        return [i for i in items if i]

    def sections(self) -> List[str]:
        return list(self._order)

    def keys(self, section: str) -> List[str]:
        merged = self._merged(section)
        return sorted(merged.keys())


# ----------------------------------------------------------------------
# Parsing utilities
# ----------------------------------------------------------------------
def _join_continuations(lines: List[str]) -> List[Tuple[int, str]]:
    """
    Join lines ending with backslash. Returns list of (first_physical_line_number, logical_line).
    Line numbers are 1‑based.
    """
    result: List[Tuple[int, str]] = []
    i = 0
    while i < len(lines):
        start = i
        line = lines[i].rstrip('\n')
        while line.endswith('\\'):
            line = line[:-1]  # remove backslash
            i += 1
            if i >= len(lines):
                break
            next_line = lines[i].lstrip()
            line += next_line.rstrip('\n')
        result.append((start + 1, line))
        i += 1
    return result


def parse(text: str):
    """
    Parse INI‑style configuration text and return a Config instance.
    """
    raw_lines = text.splitlines(keepends=True)
    logical = _join_continuations(raw_lines)

    sections: Dict[str, Dict[str, str]] = {}
    parents: Dict[str, Optional[str]] = {}
    order: List[str] = []

    current_section: Optional[str] = None

    for lineno, line in logical:
        stripped = line.lstrip()
        if not stripped or stripped[0] in ('#', ';'):
            continue  # blank or comment

        # Section header
        m_sec = _SECTION_RE.match(line)
        if m_sec:
            inner = m_sec.group(1).strip()
            # inheritance?
            m_inh = _INHERIT_RE.match(inner)
            if m_inh:
                name = m_inh.group(1).strip()
                parent = m_inh.group(2).strip()
            else:
                name = inner
                parent = None
            name = name.strip()
            if name not in sections:
                sections[name] = {}
                order.append(name)
            # merge later definitions
            if name in parents and parents[name] != parent:
                # keep original parent if already set, else set
                if parents[name] is None:
                    parents[name] = parent
            else:
                parents.setdefault(name, parent)
            current_section = name
            continue

        # Must be key/value line
        if current_section is None:
            raise ConfigError(f"line {lineno}")

        if '=' not in line:
            raise ConfigError(f"line {lineno}")

        key_part, value_part = line.split('=', 1)
        key = key_part.strip()
        if not _KEY_RE.match(key):
            raise ConfigError(f"line {lineno}")
        key_lc = key.lower()

        # Process value: handle comments and quoting
        val = value_part.lstrip()
        # Quoted value?
        if val.startswith('"'):
            # find closing quote
            i = 1
            escaped = False
            while i < len(val):
                ch = val[i]
                if escaped:
                    escaped = False
                elif ch == '\\':
                    escaped = True
                elif ch == '"':
                    break
                i += 1
            else:
                raise ConfigError(f"line {lineno}")  # unterminated

            raw_content = val[1:i]
            # process escapes
            processed = []
            j = 0
            while j < len(raw_content):
                c = raw_content[j]
                if c == '\\' and j + 1 < len(raw_content):
                    esc = raw_content[j + 1]
                    processed.append(_QUOTE_ESCAPES.get(esc, esc))
                    j += 2
                else:
                    processed.append(c)
                    j += 1
            final_val = ''.join(processed)

            # after closing quote only spaces and optional comment
            rest = val[i + 1:].strip()
            if rest:
                # possible inline comment
                if rest[0] in ('#', ';'):
                    pass
                else:
                    raise ConfigError(f"line {lineno}")
        else:
            # unquoted: strip trailing spaces, handle inline comment
            # find first # preceded by space or tab
            comment_idx = None
            for m in re.finditer(r'[ \t]([#;])', val):
                comment_idx = m.start(1)
                break
            if comment_idx is not None:
                val = val[:comment_idx - 1]  # remove the preceding space
            final_val = val.rstrip()

        sections[current_section][key_lc] = final_val

    # After parsing, verify inheritance references and cycles
    for sec, parent in parents.items():
        if parent is not None and parent not in sections:
            raise ConfigError(f"missing parent section {parent}")

    # Detect cycles (simple DFS)
    def dfs(s: str, path: Set[str]) -> None:
        if s in path:
            raise ConfigError("inheritance cycle")
        parent = parents.get(s)
        if parent:
            dfs(parent, path | {s})

    for sec in sections:
        dfs(sec, set())

    return Config(sections, parents, order)