"""Shared pytest fixtures for the cocina test suite."""
import shutil
from pathlib import Path

import pytest

from cocina.config_handler import ConfigHandler

_DOT_COCINA = Path(__file__).resolve().parents[1] / 'dot_cocina'


def _singleton_instances() -> dict:
    """Reach the @singleton decorator's instance cache for ConfigHandler.

    `singleton` (cocina/utils.py) keeps instances in a closure dict, so the only
    way to reset between tests is through the closure cell.
    """
    index = ConfigHandler.__code__.co_freevars.index('instances')
    return ConfigHandler.__closure__[index].cell_contents


@pytest.fixture(autouse=True)
def reset_config_handler():
    """ConfigHandler is a singleton; without this, config leaks between tests."""
    _singleton_instances().clear()
    yield
    _singleton_instances().clear()


@pytest.fixture
def cocina_project(tmp_path):
    """A minimal cocina project: .cocina plus empty config/ and config/args/."""
    shutil.copy(_DOT_COCINA, tmp_path / '.cocina')
    (tmp_path / 'config').mkdir()
    (tmp_path / 'config' / 'args').mkdir()
    return tmp_path


@pytest.fixture
def make_handler(cocina_project):
    """Write config/config.yaml, then build a ConfigHandler rooted at the tmp project."""
    def _make(config_yaml: str) -> ConfigHandler:
        (cocina_project / 'config' / 'config.yaml').write_text(config_yaml)
        return ConfigHandler(search_directory=str(cocina_project))
    return _make
