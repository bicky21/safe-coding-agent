"""Reference solution for the config-parser task (used only to check the task's tests)."""

import re


class ConfigError(Exception):
    pass


_MISSING = object()
_SECTION = re.compile(r"^\[\s*([^\]:]+?)\s*(?::\s*([^\]]+?)\s*)?\]$")
_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_REF = re.compile(r"\$\$|\$\{([^}]*)\}")
TRUE = {"true", "yes", "on", "1"}
FALSE = {"false", "no", "off", "0"}


def _logical_lines(text):
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        start = i
        line = lines[i].rstrip("\r")
        while line.endswith("\\") and i + 1 < len(lines):
            i += 1
            line = line[:-1] + lines[i].rstrip("\r").lstrip()
        yield start + 1, line
        i += 1


def _value(raw, lineno):
    raw = raw.strip()
    if not raw.startswith('"'):
        m = re.search(r"[ \t]#", raw)
        return (raw[:m.start()] if m else raw).strip()
    out, i = [], 1
    while i < len(raw):
        c = raw[i]
        if c == "\\" and i + 1 < len(raw):
            nxt = raw[i + 1]
            out.append({"n": "\n", '"': '"', "\\": "\\"}.get(nxt, "\\" + nxt))
            i += 2
            continue
        if c == '"':
            rest = raw[i + 1:]
            if rest.strip() and not re.match(r"^[ \t]+#", rest):
                raise ConfigError(f"unexpected text after quoted value at line {lineno}")
            return "".join(out)
        out.append(c)
        i += 1
    raise ConfigError(f"unterminated quote at line {lineno}")


class Config:
    def __init__(self):
        self._data = {}       # section -> {key: value}
        self._parent = {}     # section -> parent name
        self._order = []

    # ------------------------------------------------------------- raw access
    def _chain(self, section):
        seen, out = set(), []
        while section is not None:
            if section in seen:
                raise ConfigError(f"inheritance cycle at section {section!r}")
            seen.add(section)
            out.append(section)
            section = self._parent.get(section)
        return out

    def _raw(self, section, key):
        for s in self._chain(section):
            if key in self._data[s]:
                return self._data[s][key]
        return _MISSING

    def _resolve(self, section, key, stack):
        raw = self._raw(section, key)
        if raw is _MISSING:
            raise ConfigError(f"missing reference ${{{key}}} in section {section!r}")
        if (section, key) in stack:
            raise ConfigError(f"interpolation cycle at {section}.{key}")
        stack = stack | {(section, key)}

        def sub(m):
            if m.group(0) == "$$":
                return "$"
            ref = m.group(1).strip()
            if "." in ref:
                sec, k = ref.split(".", 1)
                if sec not in self._data:
                    raise ConfigError(f"missing section in ${{{ref}}}")
            else:
                sec, k = section, ref
            return self._resolve(sec, k.lower(), stack)

        return _REF.sub(sub, raw)

    # ------------------------------------------------------------- API
    def get(self, section, key, default=_MISSING):
        key = key.lower()
        if section not in self._data or self._raw(section, key) is _MISSING:
            if default is _MISSING:
                raise KeyError(f"{section}.{key}")
            return default
        return self._resolve(section, key, frozenset())

    def get_int(self, section, key):
        return int(self.get(section, key).strip())

    def get_float(self, section, key):
        return float(self.get(section, key).strip())

    def get_bool(self, section, key):
        v = self.get(section, key).strip().lower()
        if v in TRUE:
            return True
        if v in FALSE:
            return False
        raise ValueError(f"not a boolean: {v!r}")

    def get_list(self, section, key):
        return [p.strip() for p in self.get(section, key).split(",") if p.strip()]

    def sections(self):
        return list(self._order)

    def keys(self, section):
        if section not in self._data:
            raise KeyError(section)
        keys = set()
        for s in self._chain(section):
            keys |= set(self._data[s])
        return sorted(keys)


def parse(text):
    cfg = Config()
    current = None
    for lineno, line in _logical_lines(text):
        stripped = line.strip()
        if not stripped or stripped[0] in "#;":
            continue
        m = _SECTION.match(stripped)
        if m:
            current = m.group(1)
            if current not in cfg._data:
                cfg._data[current] = {}
                cfg._order.append(current)
            if m.group(2):
                cfg._parent[current] = m.group(2)
            continue
        if "=" not in stripped:
            raise ConfigError(f"invalid line at line {lineno}")
        key, raw = stripped.split("=", 1)
        key = key.strip()
        if current is None:
            raise ConfigError(f"key outside of a section at line {lineno}")
        if not _KEY.match(key):
            raise ConfigError(f"invalid key {key!r} at line {lineno}")
        cfg._data[current][key.lower()] = _value(raw, lineno)
    for child, parent in cfg._parent.items():
        if parent not in cfg._data:
            raise ConfigError(f"section {child!r} inherits from missing section {parent!r}")
    for s in cfg._data:
        cfg._chain(s)
    return cfg
