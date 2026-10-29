import pytest

from conf import ConfigError, parse

TEXT = """
[dev : base]
host = localhost

[base]
host = example.com
port = 80
url = http://${host}:${port}/

[prod : base]
port = 443

[app]
api = ${prod.url}api
price = $$5
"""


def test_inheritance():
    c = parse(TEXT)
    assert c.get("dev", "port") == "80"
    assert c.keys("dev") == ["host", "port", "url"]


def test_inherited_value_uses_the_child_keys():
    c = parse(TEXT)
    assert c.get("base", "url") == "http://example.com:80/"
    assert c.get("dev", "url") == "http://localhost:80/"
    assert c.get("prod", "url") == "http://example.com:443/"


def test_cross_section_reference_and_dollar():
    c = parse(TEXT)
    assert c.get("app", "api") == "http://example.com:443/api"
    assert c.get("app", "price") == "$5"


def test_multi_level_inheritance():
    c = parse("[a]\nx = 1\n[b : a]\ny = 2\n[c : b]\nz = ${x}${y}\n")
    assert c.get("c", "z") == "12"
    assert c.keys("c") == ["x", "y", "z"]


def test_missing_parent():
    with pytest.raises(ConfigError, match="ghost"):
        parse("[a : ghost]\nx = 1\n")


def test_inheritance_cycle():
    with pytest.raises(ConfigError, match="cycle"):
        parse("[a : b]\nx = 1\n[b : a]\ny = 2\n")


def test_interpolation_cycle():
    c = parse("[a]\nx = ${y}\ny = ${x}\nok = fine\n")
    assert c.get("a", "ok") == "fine"
    with pytest.raises(ConfigError, match="cycle"):
        c.get("a", "x")


def test_missing_reference():
    c = parse("[a]\nx = ${nope}\n")
    with pytest.raises(ConfigError):
        c.get("a", "x")


def test_reference_keys_are_case_insensitive():
    c = parse("[a]\nName = Ana\ngreet = hi ${NAME}\n")
    assert c.get("a", "greet") == "hi Ana"
