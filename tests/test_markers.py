"""Unit tests for the unified [[...]] grammar resolvers."""
import pytest

from cocina.utils import resolve_env_markers, resolve_markers


# --- resolve_env_markers (construction-time env pass) ---

def test_env_var_resolves_from_os_environ(monkeypatch):
    monkeypatch.setenv('REGION', 'us-west')
    out = resolve_env_markers({'p': 'buckets/[[ENV:REGION]]/data'}, None)
    assert out['p'] == 'buckets/us-west/data'


def test_env_var_missing_warns_and_empties(monkeypatch):
    monkeypatch.delenv('NOPE', raising=False)
    with pytest.warns(UserWarning, match='NOPE'):
        out = resolve_env_markers({'p': 'a/[[ENV:NOPE]]/b'}, None)
    assert out['p'] == 'a/b'  # empty substitution collapses the separator


def test_cocina_env_resolves_to_environment_name():
    out = resolve_env_markers({'p': 'runs/[[COCINA:ENV]]/x'}, 'prod')
    assert out['p'] == 'runs/prod/x'


def test_cocina_env_unset_warns_and_empties():
    with pytest.warns(UserWarning, match='COCINA:ENV'):
        out = resolve_env_markers({'p': 'a/[[COCINA:ENV]]/b'}, None)
    assert out['p'] == 'a/b'


def test_env_pass_leaves_bare_key_markers_literal():
    out = resolve_env_markers({'p': 'run/[[MODEL]]/x'}, 'prod')
    assert out['p'] == 'run/[[MODEL]]/x'


def test_env_pass_backslash_before_marker_is_ordinary():
    # No escape grammar: the backslash is a plain char and the marker still resolves.
    out = resolve_env_markers({'p': r'C:\[[COCINA:ENV]]'}, 'prod')
    assert out['p'] == r'C:\prod'


def test_env_pass_leaves_colon_content_literal():
    # A time / URL / label with a colon is not a known namespace -> left literal,
    # NOT raised, so ordinary config text never crashes the load.
    out = resolve_env_markers(
        {'a': 'open [[09:00]] close', 'b': '[[http://x.com]]'}, 'prod')
    assert out['a'] == 'open [[09:00]] close'
    assert out['b'] == '[[http://x.com]]'


def test_env_pass_supports_dotted_env_var(monkeypatch):
    monkeypatch.setenv('cocina.ENV_KEY', 'staging')
    out = resolve_env_markers({'p': '[[ENV:cocina.ENV_KEY]]'}, None)
    assert out['p'] == 'staging'


def test_reserved_cocina_namespace_typo_raises():
    with pytest.raises(ValueError, match='COCINA:NOPE'):
        resolve_env_markers({'p': '[[COCINA:NOPE]]'}, 'prod')


def test_unknown_namespace_left_literal():
    # Only ENV: and COCINA: are namespaces; anything else is literal text, not an error.
    out = resolve_env_markers({'p': '[[SECRET:TOKEN]]'}, 'prod')
    assert out['p'] == '[[SECRET:TOKEN]]'


# --- resolve_markers (per-bind render pass) ---

def test_marker_resolves_from_source():
    resolved, unresolved = resolve_markers({'p': 'run/[[MODEL]]/x'}, {'MODEL': 'owl'})
    assert resolved['p'] == 'run/owl/x'
    assert unresolved == []


def test_missing_marker_strips_to_bare_word_and_warns():
    with pytest.warns(UserWarning, match='VERSION'):
        resolved, unresolved = resolve_markers({'p': 'run/[[VERSION]]/x'}, {})
    assert resolved['p'] == 'run/VERSION/x'
    assert unresolved == ['[[VERSION]]']


def test_missing_marker_warns_once_per_key_per_pass(recwarn):
    resolve_markers({'a': '[[V]]', 'b': '[[V]]/[[V]]'}, {})
    assert len([w for w in recwarn if 'V' in str(w.message)]) == 1


def test_bindings_win_over_config_scalars():
    resolved, _ = resolve_markers({'p': '[[MODEL]]'}, {'MODEL': 'owl'})
    assert resolved['p'] == 'owl'


def test_non_string_source_value_is_stringified():
    resolved, _ = resolve_markers({'n': '[[N]]'}, {'N': 1000})
    assert resolved['n'] == '1000'


def test_runtime_values_with_quotes_and_backslashes_survive():
    resolved, _ = resolve_markers({'p': 'a/[[M]]/b'}, {'M': r'say "hi" C:\x'})
    assert resolved['p'] == r'a/say "hi" C:\x/b'


def test_empty_value_collapses_path_separator():
    resolved, _ = resolve_markers({'p': 'a/[[M]]/b'}, {'M': ''})
    assert resolved['p'] == 'a/b'


def test_markers_in_dict_keys_are_never_interpreted():
    resolved, unresolved = resolve_markers({'[[K]]': '[[K]]'}, {'K': 'v'})
    assert set(resolved.keys()) == {'[[K]]'}
    assert resolved['[[K]]'] == 'v'


def test_backslash_before_marker_is_ordinary(recwarn):
    # No escape grammar: the backslash is a plain char and the marker resolves,
    # so Windows paths render correctly instead of being silently mangled.
    resolved, unresolved = resolve_markers({'p': r'C:\[[MODEL]]\out'}, {'MODEL': 'owl'})
    assert resolved['p'] == r'C:\owl\out'
    assert unresolved == []
    assert list(recwarn) == []


@pytest.mark.parametrize(
    'template',
    [
        {'MODEL': '[[VERSION]]', 'OUT': 'runs/[[MODEL]]/data'},
        {'OUT': 'runs/[[MODEL]]/data', 'MODEL': '[[VERSION]]'},
    ],
)
def test_config_references_resolve_transitively_regardless_of_order(template):
    resolved, unresolved = resolve_markers(
        template, template, bindings={'VERSION': 'v4'})
    assert resolved['MODEL'] == 'v4'
    assert resolved['OUT'] == 'runs/v4/data'
    assert unresolved == []


def test_missing_leaf_in_chain_recovers_on_later_resolution():
    template = {'MODEL': '[[VERSION]]', 'OUT': 'runs/[[MODEL]]/data'}
    with pytest.warns(UserWarning, match='VERSION') as caught:
        first, unresolved = resolve_markers(template, template)
    assert first == {'MODEL': 'VERSION', 'OUT': 'runs/VERSION/data'}
    assert unresolved == ['[[VERSION]]']
    assert len(caught) == 1

    second, unresolved = resolve_markers(
        template, template, bindings={'VERSION': 'v4'})
    assert second == {'MODEL': 'v4', 'OUT': 'runs/v4/data'}
    assert unresolved == []


def test_binding_values_are_terminal_not_recursive_templates():
    resolved, unresolved = resolve_markers(
        {'OUT': 'runs/[[MODEL]]/data'}, {},
        bindings={'MODEL': '[[VERSION]]'})
    assert resolved['OUT'] == 'runs/[[VERSION]]/data'
    assert unresolved == []


def test_self_reference_cycle_is_reported():
    resolved, unresolved = resolve_markers({'A': '[[A]]'}, {'A': '[[A]]'})
    assert resolved['A'] == '[[A]]'
    assert unresolved == ['[[A]]']


def test_mutual_cycle_is_reported_and_binding_can_break_it(recwarn):
    template = {'A': '[[B]]', 'B': '[[A]]', 'OUT': '[[A]]'}
    cycled, unresolved = resolve_markers(template, template)
    assert set(unresolved) == {'[[A]]', '[[B]]'}
    assert any(value in ('[[A]]', '[[B]]') for value in cycled.values())
    assert list(recwarn) == []

    resolved, unresolved = resolve_markers(
        template, template, bindings={'A': 'ready'})
    assert resolved == {'A': 'ready', 'B': 'ready', 'OUT': 'ready'}
    assert unresolved == []


def test_cycle_tainted_results_are_not_cached_across_key_orders(recwarn):
    out_first = {
        'OUT': '[[A]]',
        'A': '[[B]]+[[C]]',
        'B': '[[A]]',
        'C': '[[B]]',
    }
    a_first = {
        'A': '[[B]]+[[C]]',
        'B': '[[A]]',
        'C': '[[B]]',
        'OUT': '[[A]]',
    }

    resolved_out_first, unresolved_out_first = resolve_markers(
        out_first, out_first)
    resolved_a_first, unresolved_a_first = resolve_markers(
        a_first, a_first)

    assert resolved_out_first == resolved_a_first
    cycle_members = {'[[A]]', '[[B]]', '[[C]]'}
    assert set(unresolved_out_first) == cycle_members
    assert set(unresolved_a_first) == cycle_members
    assert list(recwarn) == []


def test_bare_key_feature_preserved():
    # A value that EQUALS a source key becomes that key's value (not a bracket feature).
    resolved, _ = resolve_markers({'x': 'MODEL'}, {'MODEL': 'owl'})
    assert resolved['x'] == 'owl'


def test_old_grammars_are_no_longer_recognized():
    resolved, unresolved = resolve_markers(
        {'a': '<<BUCKET>>', 'b': '{{COCINA:MODEL}}'}, {'BUCKET': 'b'})
    assert resolved['a'] == '<<BUCKET>>'
    assert resolved['b'] == '{{COCINA:MODEL}}'
    assert unresolved == []


def test_non_key_bracket_text_is_left_literal_and_not_reported(recwarn):
    resolved, unresolved = resolve_markers({'p': 'see [[Page Title]] here'}, {})
    assert resolved['p'] == 'see [[Page Title]] here'
    assert unresolved == []
    assert [w for w in recwarn if 'Page' in str(w.message)] == []
