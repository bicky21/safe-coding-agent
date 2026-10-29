import re
from collections import OrderedDict, defaultdict
from typing import Dict, List, Optional, Tuple

# Regular expressions for parsing
_SECTION_RE = re.compile(r'\[\s*(?P<name>[^:\]]+?)\s*(?::\s*(?P<parent>[^]]+?)\s*)?\]')
_KEY_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_-]*$')
_BOOL_TRUE = {"true", "yes", "on", "1"}
_BOOL_FALSE = {"false", "no", "off", "0"}

class ConfigError(Exception):
    """Raised for syntax or semantic errors in the configuration."""
    pass

class Config:
    """Represents a parsed INI-style configuration."""

    def __init__(self):
        # Ordered sections: name -> dict of keys (lowercase) to raw values
        self._sections: "OrderedDict[str, Dict[str, str]]" = OrderedDict()
        # Inheritance graph: child -> parent
        self._parents: Dict[str, str] = {}
        # Cache for resolved values after interpolation
        self._resolved: Dict[Tuple[str, str], str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get(self, section: str, key: str, default=None) -> str:
        """Return the interpolated value for key in section."""
        section = section.strip()
        key_lc = key.strip().lower()
        if section not in self._sections:
            if default is not None:
                return default
            raise KeyError(f"section '{section}' not found")
        if key_lc not in self._all_keys(section):
            if default is not None:
                return default
            raise KeyError(f"key '{key}' not found in section '{section}'")
        return self._interpolate(section, key_lc, set())

    def get_int(self, section: str, key: str) -> int:
        return int(self.get(section, key))

    def get_float(self, section: str, key: str) -> float:
        return float(self.get(section, key))

    def get_bool(self, section: str, key: str) -> bool:
        val = self.get(section, key).strip().lower()
        if val in _BOOL_TRUE:
            return True
        if val in _BOOL_FALSE:
            return False
        raise ValueError(f"invalid boolean value: {val!r}")

    def get_list(self, section: str, key: str) -> List[str]:
        raw = self.get(section, key)
        items = [item.strip() for item in raw.split(',')]
        return [item for item in items if item]

    def sections(self) -> List[str]:
        return list(self._sections.keys())

    def keys(self, section: str) -> List[str]:
        if section not in self._sections:
            raise KeyError(f"section '{section}' not found")
        return sorted(self._all_keys(section))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _all_keys(self, section: str) -> Dict[str, str]:
        """Return a dict of all keys visible in section (including inherited)."""
        result: Dict[str, str] = {}
        visited = set()
        def collect(sec: str):
            if sec in visited:
                return
            visited.add(sec)
            if sec in self._parents:
                collect(self._parents[sec])
            for k, v in self._sections.get(sec, {}).items():
                result[k] = v
        collect(section)
        return result

    def _interpolate(self, section: str, key: str, stack: set) -> str:
        """Recursively interpolate a value."""
        cache_key = (section, key)
        if cache_key in self._resolved:
            return self._resolved[cache_key]
        if cache_key in stack:
            raise ConfigError("interpolation cycle")
        stack.add(cache_key)
        raw = self._all_keys(section)[key]
        # Replace $$ with placeholder
        raw = raw.replace("$$", "\0")
        # Find ${...}
        def repl(match):
            expr = match.group(1)
            if '.' in expr:
                sec, k = expr.split('.', 1)
                sec = sec.strip()
                k = k.strip()
                if sec not in self._sections:
                    raise ConfigError(f"missing section '{sec}' in interpolation")
                return self._interpolate(sec, k.lower(), stack)
            else:
                return self._interpolate(section, expr.lower(), stack)
        try:
            result = re.sub(r'\$\{([^}]+)\}', repl, raw)
        except RecursionError:
            raise ConfigError("interpolation cycle")
        result = result.replace("\0", "$")
        stack.remove(cache_key)
        self._resolved[cache_key] = result
        return result

def parse(text: str) -> Config:
    """Parse INI-style configuration text into a Config object."""
    cfg = Config()
    lines = text.splitlines()
    logical_lines: List[Tuple[int, str]] = []  # (first_physical_line, content)
    i = 0
    while i < len(lines):
        line = lines[i]
        first_line_num = i + 1
        # Handle continuation
        while line.rstrip().endswith('\\'):
            line = line.rstrip()[:-1] + lines[i + 1].lstrip()
            i += 1
        logical_lines.append((first_line_num, line))
        i += 1

    current_section: Optional[str] = None
    for first_line_num, line in logical_lines:
        stripped = line.strip()
        if not stripped or stripped[0] in '#;':
            continue
        # Section header
        m = _SECTION_RE.match(stripped)
        if m:
            name = m.group('name').strip()
            parent = m.group('parent')
            if parent:
                parent = parent.strip()
            if name in cfg._sections:
                # Merge: later keys win
                pass
            else:
                cfg._sections[name] = {}
            if parent:
                cfg._parents[name] = parent
            current_section = name
            continue
        # Key-value
        if current_section is None:
            raise ConfigError(f"line {first_line_num}")
        if '=' not in line:
            raise ConfigError(f"line {first_line_num}")
        key_part, value_part = line.split('=', 1)
        key = key_part.strip()
        if not _KEY_RE.match(key):
            raise ConfigError(f"line {first_line_num}")
        key_lc = key.lower()
        value = value_part.strip()
        # Handle inline comment
        if value.startswith('"'):
            # Quoted value
            if len(value) < 2 or value[-1] != '"':
                # Need to find closing quote
                # Already handled by continuation, so error
                raise ConfigError(f"line {first_line_num}")
            # Remove surrounding quotes
            inner = value[1:-1]
            # Unescape
            def unescape(s):
                return s.replace(r'\"', '"').replace(r'\\', '\\').replace(r'\n', '\n')
            value = unescape(inner)
            # After closing quote, only spaces or comment allowed
            rest = value_part[len(value_part.split('"', 2)[2]):].strip()
            if rest and not rest.startswith('#'):
                raise ConfigError(f"line {first_line_num}")
        else:
            # Unquoted: stop at comment
            if ' #' in value or '\t#' in value:
                idx = value.find('#')
                if idx != -1 and value[:idx].rstrip()[-1] in ' \t':
                    value = value[:idx].rstrip()
            # No further processing
        cfg._sections[current_section][key_lc] = value

    # Validate parents
    for child, parent in cfg._parents.items():
        if parent not in cfg._sections:
            raise ConfigError(f"missing parent section '{parent}'")
    # Detect cycles
    visited = set()
    stack = set()
    def visit(node):
        if node in stack:
            raise ConfigError("inheritance cycle")
        if node in visited:
            return
        stack.add(node)
        parent = cfg._parents.get(node)
        if parent:
            visit(parent)
        stack.remove(node)
        visited.add(node)
    for node in cfg._parents:
        visit(node)

    return cfg