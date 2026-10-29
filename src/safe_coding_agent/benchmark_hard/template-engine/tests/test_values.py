import pytest

from tmpl import render


class User:
    def __init__(self, name):
        self.name = name


def test_plain_text_is_unchanged():
    assert render("Hello, <world> & co!", {}) == "Hello, <world> & co!"


@pytest.mark.parametrize("template, context, expected", [
    ("{{ name }}", {"name": "Ana"}, "Ana"),
    ("{{name}}", {"name": "Ana"}, "Ana"),
    ("{{ user.name }}", {"user": {"name": "Bo"}}, "Bo"),
    ("{{ user.name }}", {"user": User("Cy")}, "Cy"),
    ("{{ user.address.city }}", {"user": {"address": {"city": "Pune"}}}, "Pune"),
    ("[{{ missing }}]", {}, "[]"),
    ("[{{ user.missing }}]", {"user": {"name": "x"}}, "[]"),
    ("{{ n }}", {"n": 42}, "42"),
    ("[{{ none }}]", {"none": None}, "[]"),
    ("{{ yes }}/{{ no }}", {"yes": True, "no": False}, "true/false"),
])
def test_values(template, context, expected):
    assert render(template, context) == expected


@pytest.mark.parametrize("template, context, expected", [
    ("{{ name|upper }}", {"name": "ana"}, "ANA"),
    ("{{ name | lower }}", {"name": "ANA"}, "ana"),
    ("{{ name|title }}", {"name": "ana maria"}, "Ana Maria"),
    ("{{ items|length }}", {"items": [1, 2, 3]}, "3"),
    ("{{ missing|length }}", {}, "0"),
    ('{{ items|join:", " }}', {"items": ["a", 1, None]}, "a, 1, None"),
    ('{{ name|default:"anon" }}', {}, "anon"),
    ('{{ name|default:"anon" }}', {"name": None}, "anon"),
    ('{{ name|default:"anon" }}', {"name": ""}, "anon"),
    ('{{ name|default:"anon" }}', {"name": 0}, "0"),
    ('{{ name|default:"anon"|upper }}', {}, "ANON"),
    ('{{ name|upper|default:"anon" }}', {}, "anon"),
    ('{{ name|default:"a|b" }}', {}, "a|b"),
])
def test_filters(template, context, expected):
    assert render(template, context) == expected


def test_values_are_html_escaped():
    assert render("{{ x }}", {"x": "<b>Tom & \"Jerry's\"</b>"}) == \
        "&lt;b&gt;Tom &amp; &quot;Jerry&#39;s&quot;&lt;/b&gt;"


def test_safe_disables_escaping():
    assert render("{{ x|safe }}", {"x": "<b>hi</b>"}) == "<b>hi</b>"
    assert render("{{ x|safe|upper }}", {"x": "<b>hi</b>"}) == "<B>HI</B>"


def test_escaping_happens_after_filters():
    assert render('{{ x|default:"<none>" }}', {}) == "&lt;none&gt;"
