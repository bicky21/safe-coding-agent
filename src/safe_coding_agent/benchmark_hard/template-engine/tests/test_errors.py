import pytest

from tmpl import TemplateError, render


@pytest.mark.parametrize("template, line", [
    ("line 1\n{% if a %}\nno end", 2),                         # block never closed
    ("{% for x in items %}\n{% if x %}\n{% endfor %}", 3),     # endfor while if is open
    ("ok\n\n{% endif %}", 3),                                  # endif without if
    ("{% else %}", 1),                                         # else without block
    ("{% if a %}{% else %}{% else %}{% endif %}", 1),          # second else
    ("a\nb\n{% include 'x' %}", 3),                            # unknown tag
    ("\n{{ name|shout }}", 2),                                 # unknown filter
    ("x\ny\nz {{ name", 3),                                    # unclosed {{
    ("{% if a %}\n\n{% if b", 3),                              # unclosed {%
    ("{{ 1 + 2 }}", 1),                                        # invalid expression
])
def test_errors_report_the_line(template, line):
    with pytest.raises(TemplateError, match=f"line {line}"):
        render(template, {"a": True, "items": [1]})


def test_error_is_an_exception_subclass():
    assert issubclass(TemplateError, Exception)
