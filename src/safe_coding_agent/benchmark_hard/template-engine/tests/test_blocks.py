import pytest

from tmpl import render


@pytest.mark.parametrize("context, expected", [
    ({"a": True}, "A"),
    ({"a": False, "b": 1}, "B"),
    ({"a": 0, "b": []}, "C"),
    ({}, "C"),
])
def test_if_elif_else(context, expected):
    t = "{% if a %}A{% elif b %}B{% else %}C{% endif %}"
    assert render(t, context) == expected


def test_if_not_and_dotted():
    t = "{% if not user.admin %}guest{% endif %}"
    assert render(t, {"user": {"admin": False}}) == "guest"
    assert render(t, {"user": {"admin": True}}) == ""
    assert render(t, {}) == "guest"


def test_for_loop_with_loop_variables():
    t = "{% for x in items %}{{ loop.index }}/{{ loop.length }}:{{ x }}" \
        "{% if loop.first %}(first){% endif %}{% if loop.last %}(last){% endif %} {% endfor %}"
    assert render(t, {"items": ["a", "b", "c"]}) == "1/3:a(first) 2/3:b 3/3:c(last) "


@pytest.mark.parametrize("context", [{"items": []}, {"items": None}, {}])
def test_for_else(context):
    assert render("{% for x in items %}{{ x }}{% else %}empty{% endfor %}", context) == "empty"


def test_nested_loops_and_shadowing():
    t = ("{% for row in rows %}{% for x in row %}{{ loop.index }}{{ x }}{% endfor %}"
         "|{{ loop.index }};{% endfor %}{{ x }}")
    assert render(t, {"rows": [["a", "b"], ["c"]], "x": "outer"}) == "1a2b|1;1c|2;outer"


def test_loop_over_dicts_with_dotted_names():
    t = "{% for u in users %}{{ u.name|upper }}{% if not loop.last %}, {% endif %}{% endfor %}"
    assert render(t, {"users": [{"name": "ana"}, {"name": "bo"}]}) == "ANA, BO"


def test_comments_produce_nothing():
    assert render("a{# a comment with {{ x }} inside #}b", {"x": 1}) == "ab"


def test_whitespace_control():
    t = "<ul>\n  {%- for x in items %}\n  <li>{{ x }}</li>\n  {%- endfor %}\n</ul>"
    assert render(t, {"items": [1, 2]}) == "<ul>\n  <li>1</li>\n  <li>2</li>\n</ul>"
    assert render("a   {{- x -}}   b", {"x": "X"}) == "aXb"
    assert render("a\n\n {%- if t -%} \n\n b {%- endif %}", {"t": True}) == "ab"
