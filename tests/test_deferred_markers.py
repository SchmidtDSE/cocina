"""Tests for deferred {{COCINA:KEY}} markers and bind()."""
from cocina.utils import bind_deferred_values, unresolved_deferred


def test_fixtures_build_a_working_config_handler(make_handler):
    handler = make_handler('BUCKET: b\nOUT: "<<BUCKET>>/out"\n')
    assert handler.config == {'BUCKET': 'b', 'OUT': 'b/out'}


def test_bind_resolves_provided_markers():
    out = bind_deferred_values(
        {'p': 'run/{{COCINA:MODEL}}/{{COCINA:VERSION}}/r.jsonl'},
        MODEL='owl', VERSION='v4')
    assert out['p'] == 'run/owl/v4/r.jsonl'


def test_bind_leaves_unprovided_markers_intact():
    out = bind_deferred_values({'p': 'run/{{COCINA:M}}/{{COCINA:V}}/x'}, M='owl')
    assert out['p'] == 'run/owl/{{COCINA:V}}/x'


def test_staged_binding():
    config = {'p': 'run/{{COCINA:M}}/{{COCINA:V}}/x'}
    config = bind_deferred_values(config, M='owl')
    config = bind_deferred_values(config, V='v4')
    assert config['p'] == 'run/owl/v4/x'


def test_bind_recurses_into_nested_structures():
    out = bind_deferred_values(
        {'a': {'b': ['run/{{COCINA:M}}/x', 'run/{{COCINA:M}}/y']}}, M='owl')
    assert out == {'a': {'b': ['run/owl/x', 'run/owl/y']}}


def test_bind_escapes_backslashes():
    """Runtime values come from model cards and external services, not config."""
    out = bind_deferred_values({'p': 'a/{{COCINA:M}}/b'}, M=r'C:\models')
    assert out['p'] == 'a/C:\\models/b'


def test_bind_escapes_quotes():
    out = bind_deferred_values({'p': 'a/{{COCINA:M}}/b'}, M='say "hi"')
    assert out['p'] == 'a/say "hi"/b'


def test_bind_stringifies_non_string_values():
    out = bind_deferred_values({'n': '{{COCINA:N}}'}, N=1000)
    assert out['n'] == '1000'


def test_bind_empty_value_collapses_path_separator():
    out = bind_deferred_values({'p': 'a/{{COCINA:M}}/b'}, M='')
    assert out['p'] == 'a/b'


def test_unresolved_deferred_reports_leftovers():
    assert unresolved_deferred({'p': 'run/{{COCINA:MODEL}}/x'}) == ['{{COCINA:MODEL}}']
    assert unresolved_deferred({'p': 'run/owl/x'}) == []


def test_unresolved_ignores_bare_double_brace_templates():
    """The COCINA: namespace is what keeps stored Jinja/Handlebars out of unresolved()."""
    stored_template = {'body': 'Hello {{NAME}}, see {{ user.profile }}'}
    assert unresolved_deferred(stored_template) == []
