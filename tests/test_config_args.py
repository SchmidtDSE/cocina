"""ConfigArgs instance-local resolution under the unified [[...]] grammar."""
import pytest

from cocina.config_handler import ConfigArgs, ConfigHandler


@pytest.fixture
def job_args(cocina_project):
    """A project with config.yaml plus config/args/my_job.yaml, handler primed."""
    (cocina_project / 'config' / 'config.yaml').write_text(
        'BUCKET: b\nRESULTS: "[[BUCKET]]/[[MODEL]]/r.jsonl"\n')
    (cocina_project / 'config' / 'args' / 'my_job.yaml').write_text(
        'run:\n'
        '  kwargs:\n'
        '    out_dir: "out/[[MODEL]]/[[VERSION]]"\n'
        '    limit: 5\n')
    ConfigHandler(search_directory=str(cocina_project))
    return ConfigArgs('my_job')


def test_binds_arg_sections(job_args):
    job_args.bind(MODEL='owl', VERSION='v4')
    assert job_args.run.kwargs == {'out_dir': 'out/owl/v4', 'limit': 5}


def test_args_resolve_through_transitive_config_source(cocina_project):
    (cocina_project / 'config' / 'config.yaml').write_text(
        'VERSION: v4\nMODEL: "[[VERSION]]"\n')
    (cocina_project / 'config' / 'args' / 'my_job.yaml').write_text(
        'run:\n  kwargs:\n    out: "runs/[[MODEL]]/data"\n')
    handler = ConfigHandler(search_directory=str(cocina_project))
    args = ConfigArgs('my_job', config_handler=handler)
    assert args.run.kwargs['out'] == 'runs/v4/data'
    assert args.unresolved() == []


def test_binds_config_values(job_args):
    job_args.bind(MODEL='owl')
    assert job_args.RESULTS == 'b/owl/r.jsonl'


def test_args_template_is_pristine(job_args):
    job_args.bind(MODEL='owl')
    assert job_args.args_template['run']['kwargs']['out_dir'] == 'out/[[MODEL]]/[[VERSION]]'


def test_bind_returns_self_for_chaining(job_args):
    assert job_args.bind(MODEL='owl') is job_args


def test_unresolved_spans_config_and_args(job_args):
    assert set(job_args.unresolved()) == {'[[MODEL]]', '[[VERSION]]'}
    job_args.bind(MODEL='owl', VERSION='v4')
    assert job_args.unresolved() == []


def test_unresolved_preserves_first_seen_order_without_duplicates(job_args):
    # MODEL appears in both config (RESULTS) and args (out_dir); reported once.
    assert job_args.unresolved() == ['[[MODEL]]', '[[VERSION]]']


def test_rebind_flag_reresolves_args(job_args):
    job_args.bind(MODEL='owl', VERSION='v4')
    job_args.bind(MODEL='birdnet', rebind=True)
    assert job_args.run.kwargs['out_dir'] == 'out/birdnet/v4'


def test_rebind_without_flag_raises_and_leaves_args(job_args):
    job_args.bind(MODEL='owl')
    with pytest.raises(ValueError, match='rebind=True'):
        job_args.bind(MODEL='birdnet', VERSION='v4')
    assert job_args.run.kwargs['out_dir'] == 'out/owl/VERSION'


def test_bind_from_dict(job_args):
    job_args.bind({'MODEL': 'owl', 'VERSION': 'v4'})
    assert job_args.run.kwargs == {'out_dir': 'out/owl/v4', 'limit': 5}
    assert job_args.RESULTS == 'b/owl/r.jsonl'


def test_bind_from_yaml_path(job_args, cocina_project):
    (cocina_project / 'card.yaml').write_text('MODEL: owl\nVERSION: v4\n')
    job_args.bind('card.yaml')
    assert job_args.run.kwargs == {'out_dir': 'out/owl/v4', 'limit': 5}


def test_two_instances_do_not_leak_sections(cocina_project):
    (cocina_project / 'config' / 'config.yaml').write_text('BUCKET: b\n')
    (cocina_project / 'config' / 'args' / 'job_a.yaml').write_text(
        'run:\n  kwargs:\n    out: "a/[[MODEL]]"\n')
    (cocina_project / 'config' / 'args' / 'job_b.yaml').write_text(
        'run:\n  kwargs:\n    out: "b/[[SIZE]]"\n')
    ConfigHandler(search_directory=str(cocina_project))
    ca_a = ConfigArgs('job_a')
    ca_b = ConfigArgs('job_b')
    ca_a.bind(MODEL='owl')
    assert ca_a.run.kwargs['out'] == 'a/owl'
    assert ca_b.run.kwargs['out'] == 'b/SIZE'          # ca_a's bind did not touch ca_b's template
    assert ca_b.unresolved() == ['[[SIZE]]']           # only ca_b's own marker
