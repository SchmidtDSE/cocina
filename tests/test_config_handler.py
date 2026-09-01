"""ConfigHandler behavior under the unified [[...]] grammar."""
import pytest


def test_marker_resolves_from_config_sibling_at_load(make_handler):
    handler = make_handler('BUCKET: b\nOUT: "[[BUCKET]]/out"\n')
    assert handler.config == {'BUCKET': 'b', 'OUT': 'b/out'}


def test_config_reference_chain_resolves_at_load(make_handler):
    handler = make_handler(
        'VERSION: v4\nMODEL: "[[VERSION]]"\n'
        'OUT: "runs/[[MODEL]]/data"\n')
    assert handler.config == {
        'VERSION': 'v4', 'MODEL': 'v4', 'OUT': 'runs/v4/data'}
    assert handler.unresolved() == []


def test_deferred_leaf_resolves_entire_chain_after_bind(make_handler):
    with pytest.warns(UserWarning, match='VERSION'):
        handler = make_handler(
            'MODEL: "[[VERSION]]"\nOUT: "runs/[[MODEL]]/data"\n')
    assert handler.config['OUT'] == 'runs/VERSION/data'
    assert handler.unresolved() == ['[[VERSION]]']

    handler.bind(VERSION='v4')
    assert handler.config['MODEL'] == 'v4'
    assert handler.config['OUT'] == 'runs/v4/data'
    assert handler.unresolved() == []
    assert handler.template['MODEL'] == '[[VERSION]]'


def test_rebind_reresolves_transitive_dependents(make_handler):
    handler = make_handler(
        'MODEL: "[[VERSION]]"\nOUT: "runs/[[MODEL]]/data"\n')
    handler.bind(VERSION='v4')
    handler.bind(VERSION='v5', rebind=True)
    assert handler.config['MODEL'] == 'v5'
    assert handler.config['OUT'] == 'runs/v5/data'


def test_binding_breaks_config_reference_cycle(make_handler, recwarn):
    handler = make_handler(
        'A: "[[B]]"\nB: "[[A]]"\nOUT: "[[A]]"\n')
    assert set(handler.unresolved()) == {'[[A]]', '[[B]]'}
    assert list(recwarn) == []

    handler.bind(A='ready')
    assert handler.config == {'A': 'ready', 'B': 'ready', 'OUT': 'ready'}
    assert handler.unresolved() == []


def test_handler_passes_marker_shaped_binding_as_terminal(make_handler, recwarn):
    with pytest.warns(UserWarning, match='MODEL'):
        handler = make_handler('OUT: "[[MODEL]]"\n')
    recwarn.clear()

    handler.bind(MODEL='[[VERSION]]')
    assert handler.config['OUT'] == '[[VERSION]]'
    assert handler.unresolved() == []
    assert list(recwarn) == []


def test_template_is_pristine_and_config_is_derived(make_handler):
    with pytest.warns(UserWarning, match='MODEL'):        # warns at construction
        handler = make_handler('P: "run/[[MODEL]]/x"\n')
    assert handler.template['P'] == 'run/[[MODEL]]/x'     # marker stays literal
    assert handler.config['P'] == 'run/MODEL/x'          # derived view: strip applied


def test_unresolved_reports_missing_marker_without_warning(make_handler, recwarn):
    with pytest.warns(UserWarning):
        handler = make_handler('P: "run/[[MODEL]]/x"\n')
    recwarn.clear()
    assert handler.unresolved() == ['[[MODEL]]']
    assert list(recwarn) == []  # unresolved() itself never warns


def test_bind_resolves_from_pristine_template(make_handler):
    handler = make_handler('P: "run/[[MODEL]]/[[VERSION]]/x"\n')
    handler.bind(MODEL='owl', VERSION='v4')
    assert handler.config['P'] == 'run/owl/v4/x'
    assert handler.template['P'] == 'run/[[MODEL]]/[[VERSION]]/x'  # unchanged
    assert handler.unresolved() == []


def test_staged_binding_shrinks_unresolved(make_handler):
    handler = make_handler('P: "run/[[MODEL]]/[[VERSION]]/x"\n')
    handler.bind(MODEL='owl')
    assert handler.config['P'] == 'run/owl/VERSION/x'
    assert handler.unresolved() == ['[[VERSION]]']
    handler.bind(VERSION='v4')
    assert handler.config['P'] == 'run/owl/v4/x'
    assert handler.unresolved() == []


def test_rebinding_same_value_is_a_noop(make_handler):
    handler = make_handler('P: "[[MODEL]]"\n')
    handler.bind(MODEL='owl')
    handler.bind(MODEL='owl')  # no raise
    assert handler.config['P'] == 'owl'


def test_rebinding_different_value_raises_without_rebind_flag(make_handler):
    handler = make_handler('P: "[[MODEL]]"\n')
    handler.bind(MODEL='owl')
    with pytest.raises(ValueError, match='rebind=True'):
        handler.bind(MODEL='birdnet')
    assert handler.config['P'] == 'owl'


def test_rebind_flag_reresolves_from_template(make_handler):
    handler = make_handler('P: "[[MODEL]]"\n')
    handler.bind(MODEL='owl')
    handler.bind(MODEL='birdnet', rebind=True)
    assert handler.config['P'] == 'birdnet'


def test_bind_overrides_config_defined_value(make_handler):
    handler = make_handler('MODEL: default\nP: "[[MODEL]]"\n')
    assert handler.config['P'] == 'default'
    handler.bind(MODEL='owl')
    assert handler.config['P'] == 'owl'


def test_bind_from_dict(make_handler):
    handler = make_handler('P: "run/[[MODEL]]/[[VERSION]]/x"\n')
    handler.bind({'MODEL': 'owl', 'VERSION': 'v4'})
    assert handler.config['P'] == 'run/owl/v4/x'


def test_bind_from_yaml_path(make_handler, cocina_project):
    (cocina_project / 'card.yaml').write_text('MODEL: owl\nVERSION: v4\n')
    handler = make_handler('P: "run/[[MODEL]]/[[VERSION]]/x"\n')
    handler.bind('card.yaml')
    assert handler.config['P'] == 'run/owl/v4/x'


def test_bind_raises_on_key_in_both_arg_and_kwarg(make_handler):
    handler = make_handler('P: "[[MODEL]]"\n')
    with pytest.raises(ValueError, match='both \\*args and \\*\\*values'):
        handler.bind({'MODEL': 'owl'}, MODEL='birdnet')


def test_bind_raises_on_key_in_two_positional_args(make_handler):
    handler = make_handler('P: "[[MODEL]]"\n')
    with pytest.raises(ValueError, match='more than one source'):
        handler.bind({'MODEL': 'owl'}, {'MODEL': 'birdnet'})


def test_bind_rejects_bad_arg_type(make_handler):
    handler = make_handler('P: "[[MODEL]]"\n')
    with pytest.raises(ValueError, match='string.*or.*dict'):
        handler.bind(123)


def test_colon_bracket_content_loads_literal(make_handler):
    # A value with unrecognized [[x:y]] content loads without crashing and stays literal.
    handler = make_handler("T: 'window [[09:00]] open'\n")
    assert handler.config['T'] == 'window [[09:00]] open'
    assert handler.unresolved() == []


def test_backslash_before_marker_is_ordinary(make_handler):
    # No escape grammar: the backslash is a plain char and the marker still binds.
    handler = make_handler("P: 'C:\\[[MODEL]]\\out'\n")  # single-quoted YAML -> one backslash
    handler.bind(MODEL='owl')
    assert handler.config['P'] == 'C:\\owl\\out'


def test_update_replaces_template_and_reresolves_with_bindings(make_handler):
    handler = make_handler('P: "run/[[MODEL]]/x"\n')
    handler.bind(MODEL='owl')
    handler.update({'Q': 'out/[[MODEL]]/y'})
    assert handler.config['P'] == 'run/owl/x'   # existing binding preserved
    assert handler.config['Q'] == 'out/owl/y'   # binding overrides an updated key's marker


def test_update_binding_still_overrides_updated_config_key(make_handler):
    handler = make_handler('P: "[[MODEL]]"\n')
    handler.bind(MODEL='owl')
    handler.update(MODEL='from_config')     # a real config value for MODEL
    assert handler.config['P'] == 'owl'     # binding wins over the updated config value


def test_reserved_namespace_typo_errors_at_construction(make_handler):
    with pytest.raises(ValueError, match='COCINA:NOPE'):
        make_handler('P: "[[COCINA:NOPE]]"\n')
