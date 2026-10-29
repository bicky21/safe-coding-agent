import re
from collections import OrderedDict, defaultdict
from typing import Dict, List, Optional, Tuple

# Regular expressions
_KEY_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_-]*$')
_INTERP_RE = re.compile(r'\$\$|\$\{([^}]+)\}')

class ConfigError(Exception):
    """Raised for any parsing or interpolation error."""
    pass

class Config:
    """Represents a parsed INI configuration."""
    def __init__(self):
        # sections: name -> dict of key->value (raw, un-interpolated)
        self._sections: Dict[str, Dict[str, str]] = OrderedDict()
        # inheritance: child -> parent
        self._inherit: Dict[str, str] = {}
        # order of first appearance
        self._order: List[str] = []

    def _add_section(self, name: str):
        if name not in self._sections:
            self._sections[name] = {}
            self._order.append(name)

    def _merge_section(self, name: str, data: Dict[str, str]):
        self._add_section(name)
        self._sections[name].update(data)

    def _resolve_inheritance(self):
        # Detect missing parents
        for child, parent in self._inherit.items():
            if parent not in self._sections:
                raise ConfigError(f"parent section '{parent}' not found")
        # Detect cycles
        visited = {}
        def visit(node, stack):
            if node in stack:
                raise ConfigError("inheritance cycle detected")
            if node in visited:
                return
            stack.add(node)
            parent = self._inherit.get(node)
            if parent:
                visit(parent, stack)
            stack.remove(node)
            visited[node] = True
        for child in self._inherit:
            visit(child, set())
        # Merge parents into children
        for child, parent in self._inherit.items():
            merged = {}
            # recursively gather parents
            def gather(sec):
                if sec in self._inherit:
                    gather(self._inherit[sec])
                merged.update(self._sections[sec])
            gather(parent)
            # child overrides
            merged.update(self._sections[child])
            self._sections[child] = merged

    def get(self, section: str, key: str, default=None) -> str:
        sec = self._sections.get(section)
        if sec is None:
            # Return default if provided, otherwise raise KeyError
            if default is not None or default is None:
                return default
            raise KeyError(section)
        k = key.lower()
        if k not in sec:
            if default is not None or default is None:
                return default
            raise KeyError(key)
        raw = sec[k]
        return self._interpolate(section, raw, set())

    def _interpolate(self, section: str, value: str, stack: set) -> str:
        def repl(match):
            token = match.group(1)
            if token is None:
                return '$'
            if '.' in token:
                sec_name, key_name = token.split('.', 1)
                if sec_name not in self._sections:
                    raise ConfigError(f"missing section '{sec_name}'")
                ref_val = self._sections[sec_name].get(key_name.lower())
                if ref_val is None:
                    raise ConfigError(f"missing key '{key_name}' in section '{sec_name}'")
                if (sec_name, key_name.lower()) in stack:
                    raise ConfigError("interpolation cycle detected")
                stack.add((sec_name, key_name.lower()))
                res = self._interpolate(sec_name, ref_val, stack)
                stack.remove((sec_name, key_name.lower()))
                return res
            else:
                key_name = token
                ref_val = self._sections[section].get(key_name.lower())
                if ref_val is None:
                    raise ConfigError(f"missing key '{key_name}' in section '{section}'")
                if (section, key_name.lower()) in stack:
                    raise ConfigError("interpolation cycle detected")
                stack.add((section, key_name.lower()))
                res = self._interpolate(section, ref_val, stack)
                stack.remove((section, key_name.lower()))
                return res
        return _INTERP_RE.sub(repl, value)

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
        if section not in self._sections:
            raise KeyError(section)
        return sorted(self._sections[section].keys())

def parse(text: str) -> Config:
    cfg = Config()
    lines = text.splitlines()
    logical_lines: List[Tuple[int, str]] = []
    i = 0
    while i < len(lines):
        line_no = i + 1
        line = lines[i]
        # handle continuation
        while line.endswith('\\'):
            line = line[:-1] + lines[i+1].lstrip()
            i += 1
            if i >= len(lines):
                break
        logical_lines.append((line_no, line))
        i += 1

    current_section = None
    for line_no, line in logical_lines:
        stripped = line.strip()
        if not stripped or stripped[0] in ('#', ';'):
            continue
        if stripped.startswith('[') and stripped.endswith(']'):
            # section header
            header = stripped[1:-1].strip()
            if ':' in header:
                child, parent = [h.strip() for h in header.split(':', 1)]
                if not child or not parent:
                    raise ConfigError(f"line {line_no}")
                cfg._inherit[child] = parent
                cfg._add_section(child)
                current_section = child
            else:
                name = header
                if not name:
                    raise ConfigError(f"line {line_no}")
                cfg._add_section(name)
                current_section = name
            continue
        # key=value
        if current_section is None:
            raise ConfigError(f"line {line_no}")
        if '=' not in line:
            raise ConfigError(f"line {line_no}")
        key_part, value_part = line.split('=', 1)
        key = key_part.strip()
        if not _KEY_RE.match(key):
            raise ConfigError(f"line {line_no}")
        value = value_part.strip()
        # handle quoted
        if value.startswith('"'):
            if not value.endswith('"'):
                # find closing quote
                end = 1
                escaped = False
                while end < len(value):
                    c = value[end]
                    if escaped:
                        escaped = False
                    elif c == '\\':
                        escaped = True
                    elif c == '"':
                        break
                    end += 1
                if end >= len(value) or value[end] != '"':
                    raise ConfigError(f"line {line_no}")
                raw = value[1:end]
                rest = value[end+1:].strip()
                if rest and not rest.startswith('#'):
                    raise ConfigError(f"line {line_no}")
                # unescape
                def unescape(s):
                    return s.replace(r'\"', '"').replace(r'\\', '\\').replace(r'\n', '\n')
                value = unescape(raw)
            else:
                raw = value[1:-1]
                def unescape(s):
                    return s.replace(r'\"', '"').replace(r'\\', '\\').replace(r'\n', '\n')
                value = unescape(raw)
        else:
            # inline comment: only if a space or tab precedes #
            # find first # preceded by space or tab
            idx = None
            for m in re.finditer(r'[ \t]#', value):
                idx = m.start() + 1
                break
            if idx is not None:
                value = value[:idx].rstrip()
        cfg._merge_section(current_section, {key.lower(): value})
    cfg._resolve_inheritance()
    return cfg