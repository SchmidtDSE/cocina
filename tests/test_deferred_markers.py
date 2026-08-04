"""Tests for deferred {{COCINA:KEY}} markers and bind()."""
import pytest

from cocina.utils import bind_deferred_values, unresolved_deferred
from cocina.config_handler import ConfigArgs, ConfigHandler


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


def test_bare_double_brace_template_survives_config_load(make_handler):
    """A config holding an ordinary template string is untouched and not reported."""
    handler = make_handler(
        'PROMPT: "Hello {{NAME}}, see {{ user.profile }}"\n'
        'P: "run/{{COCINA:MODEL}}/x"\n')
    assert handler.config['PROMPT'] == 'Hello {{NAME}}, see {{ user.profile }}'
    assert handler.unresolved() == ['{{COCINA:MODEL}}']


def test_process_values_leaves_deferred_untouched(make_handler):
    """<<KEY>> resolves at load time; {{COCINA:KEY}} must survive for bind()."""
    handler = make_handler('BUCKET: b\nP: "<<BUCKET>>/{{COCINA:MODEL}}/r.jsonl"\n')
    assert handler.config['P'] == 'b/{{COCINA:MODEL}}/r.jsonl'


def test_config_handler_bind_and_unresolved(make_handler):
    handler = make_handler('P: "run/{{COCINA:MODEL}}/{{COCINA:VERSION}}/x"\n')
    assert set(handler.unresolved()) == {'{{COCINA:MODEL}}', '{{COCINA:VERSION}}'}
    handler.bind(MODEL='owl', VERSION='v4')
    assert handler.config['P'] == 'run/owl/v4/x'
    assert handler.unresolved() == []


def test_config_handler_binds_in_stages(make_handler):
    handler = make_handler('P: "run/{{COCINA:MODEL}}/{{COCINA:VERSION}}/x"\n')
    handler.bind(MODEL='owl')
    assert handler.config['P'] == 'run/owl/{{COCINA:VERSION}}/x'
    handler.bind(VERSION='v4')
    assert handler.config['P'] == 'run/owl/v4/x'


def test_config_handler_rebind_raises(make_handler):
    """A second bind would silently no-op - the marker is already gone - so it raises."""
    handler = make_handler('P: "run/{{COCINA:MODEL}}/x"\n')
    handler.bind(MODEL='owl')
    with pytest.raises(ValueError, match='already bound'):
        handler.bind(MODEL='birdnet')
    assert handler.config['P'] == 'run/owl/x'


@pytest.fixture
def job_args(cocina_project):
    """A project with config.yaml plus config/args/my_job.yaml, handler primed."""
    (cocina_project / 'config' / 'config.yaml').write_text(
        'BUCKET: b\nRESULTS: "<<BUCKET>>/{{COCINA:MODEL}}/r.jsonl"\n')
    (cocina_project / 'config' / 'args' / 'my_job.yaml').write_text(
        'run:\n'
        '  kwargs:\n'
        '    out_dir: "out/{{COCINA:MODEL}}/{{COCINA:VERSION}}"\n'
        '    limit: 5\n')
    ConfigHandler(search_directory=str(cocina_project))
    return ConfigArgs('my_job')


def test_config_args_binds_arg_sections(job_args):
    job_args.bind(MODEL='owl', VERSION='v4')
    assert job_args.run.kwargs == {'out_dir': 'out/owl/v4', 'limit': 5}


def test_config_args_binds_config_values(job_args):
    job_args.bind(MODEL='owl')
    assert job_args.RESULTS == 'b/owl/r.jsonl'


def test_config_args_bind_returns_self_for_chaining(job_args):
    assert job_args.bind(MODEL='owl') is job_args


def test_config_args_unresolved_spans_config_and_args(job_args):
    assert set(job_args.unresolved()) == {'{{COCINA:MODEL}}', '{{COCINA:VERSION}}'}
    job_args.bind(MODEL='owl', VERSION='v4')
    assert job_args.unresolved() == []


def test_config_args_rebind_raises_and_leaves_args_untouched(job_args):
    job_args.bind(MODEL='owl')
    with pytest.raises(ValueError, match='already bound'):
        job_args.bind(MODEL='birdnet', VERSION='v4')
    assert job_args.run.kwargs['out_dir'] == 'out/owl/{{COCINA:VERSION}}'
