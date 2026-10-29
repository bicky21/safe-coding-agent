import pytest

from conf import ConfigError, parse

BASIC = """
# a comment
; another comment
[server]
Host = example.com
port=8080
path = /api#v1          # the first # has no space before it
debug = yes

[Paths]
root = "  /srv/data  "  # quoted: spaces kept
motto = "say \\"hi\\"\\nbye\\\\"
"""


def test_basic_values():
    c = parse(BASIC)
    assert c.get("server", "host") == "example.com"
    assert c.get("server", "HOST") == "example.com"
    assert c.get("server", "port") == "8080"
    assert c.get("server", "path") == "/api#v1"
    assert c.get("Paths", "root") == "  /srv/data  "
    assert c.get("Paths", "motto") == 'say "hi"\nbye\\'


def test_sections_and_keys():
    c = parse(BASIC)
    assert c.sections() == ["server", "Paths"]
    assert c.keys("server") == ["debug", "host", "path", "port"]
    with pytest.raises(KeyError):
        c.keys("paths")              # section names keep their case


def test_typed_getters():
    c = parse("[a]\nn = 42\nf = 2.5\nb1 = On\nb2 = NO\nbad = maybe\nl = a, b ,, c ,\n")
    assert c.get_int("a", "n") == 42
    assert c.get_float("a", "f") == 2.5
    assert c.get_bool("a", "b1") is True
    assert c.get_bool("a", "b2") is False
    with pytest.raises(ValueError):
        c.get_bool("a", "bad")
    assert c.get_list("a", "l") == ["a", "b", "c"]


def test_missing_and_default():
    c = parse("[a]\nx = 1\n")
    with pytest.raises(KeyError):
        c.get("a", "y")
    with pytest.raises(KeyError):
        c.get("nope", "x")
    assert c.get("a", "y", "dflt") == "dflt"
    assert c.get("nope", "x", None) is None


def test_continuation_lines():
    c = parse("[a]\nlong = one \\\n      two \\\n   three\nnext = 2\n")
    assert c.get("a", "long") == "one two three"
    assert c.get("a", "next") == "2"


def test_duplicates_merge_and_last_wins():
    c = parse("[a]\nx = 1\ny = 1\n[b]\nz = 1\n[a]\nx = 2\n")
    assert c.get("a", "x") == "2" and c.get("a", "y") == "1"
    assert c.sections() == ["a", "b"]


@pytest.mark.parametrize("text, line", [
    ("x = 1\n[a]", 1),                          # key before any section
    ("[a]\n\njust words", 3),                   # not a section/key/comment
    ("[a]\n1bad = x", 2),                       # invalid key
    ("[a]\nok = 1\ns = \"open", 3),            # unterminated quote
    ("[a]\ns = \"x\" junk", 2),                 # text after the closing quote
    ("[a]\nv = 1\nbad \\\n  still bad", 3),     # continuation: first physical line
])
def test_syntax_errors_report_the_line(text, line):
    with pytest.raises(ConfigError, match=f"line {line}"):
        parse(text)
