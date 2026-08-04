"""Tests for deferred {{COCINA:KEY}} markers and bind()."""


def test_fixtures_build_a_working_config_handler(make_handler):
    handler = make_handler('BUCKET: b\nOUT: "<<BUCKET>>/out"\n')
    assert handler.config == {'BUCKET': 'b', 'OUT': 'b/out'}
