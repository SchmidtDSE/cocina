import os
import re
import importlib
from typing import Any, List, Optional, Union
from pathlib import Path
from project_kit import constants as c
from project_kit import utils


class ConfigHandler():

    def __init__(self, module_path=None):
        """
        """
        self.project_root = utils.dir_search(c.PKIT_CONFIG_FILENAME)
        self.pkit_config = utils.read_yaml(f'{self.project_root}/{c.PKIT_CONFIG_FILENAME}')
        self.constants = self._import_constants(module_path)
        self.config = self._load_config()
        self._check_protected_keys()

    def update(self, **kwargs):
        self.config.update(kwargs)



    def get(self, key: str, default: Any = None) -> Any:
        """ get value with default
        Usage:

            c.get('some_key')

            NOTE THE RECURSIVE SEARCH. IF VALUE IS ALL UPPERCASE
            AND VALUE IS A KEY in ch THEN GRAB THAT VALUE INSTEAD

        Args:

            key (str): key to access
            default (Any = None): default value
        """
        value = getattr(self.constants, key, c.PKIT_NOT_FOUND)
        if value == c.PKIT_NOT_FOUND:
            value = self.config.get(key, default)
        if isinstance(value, str) and value.isupper() and (value in self):
            value = self[value]
        return value



    def __contains__(self, key) -> Union[bool, None]:
        """ get value (throws error if key does not exist)
        Usage: key in c

        Args:

            key (str): key to access
        """
        if isinstance(key, str):
            contains = key in self.config
            if not contains:
                contains = hasattr(self.constants, key)
            return contains


    def __getitem__(self, key) -> Any:
        """ get value (throws error if key does not exist)
        Usage: c['some_key']

        Args:

            key (str): key to access
        """
        value = self.get(key, c.PKIT_NOT_FOUND)
        if value == c.PKIT_NOT_FOUND:
            print(self.config)
            raise KeyError(f'{key} not found in config, or constants')
        else:
            return value


    def __getattr__(self, key) -> Any:
        """ get value (throws error if key does not exist)
        Usage: c.some_key

        Args:

            key (str): key to access
        """
        return self.__getitem__(key)


    def __repr__(self):
        rep = (
                f'ConfigHandler:\n'
                f'- constants: {self.constants}\n'
                f'- config: {self.config}')
        return rep


    #
    # INTERNAL
    #
    def _import_constants(self, module_path):
        """ imports constants module if it exists"""
        constants_module = None
        if module_path:
            module_path =  str(Path(module_path).resolve())
            module_name = re.sub(f'{self.project_root}/', '', module_path).split('/', 1)[0]
            try:
                constants_module = importlib.import_module(f'{module_name}.{self.pkit_config["constants_module_name"]}')
            except:
                pass
        return constants_module


    def _load_config(self):
        """ loads configuration, adding env-config if exists
        """
        config_dir = f'{self.project_root}/{self.pkit_config["config_folder"]}'
        config = utils.read_yaml(f'{config_dir}/{self.pkit_config["config_filename"]}')
        default_env = config.pop(self.pkit_config['default_env_key'], None)
        env = os.environ.get(self.pkit_config['project_kit_env_var_name'], default_env)
        if env:
            config.update(utils.read_yaml(f'{config_dir}/{env}.yaml'))
        return config


    def _check_protected_keys(self):
        """ ensures that user's config files do not attempt to overwrite user's constants.py
        """
        if self.constants:
            protected_keys = dir(self.constants)
            protected_keys = [k for k in protected_keys if str(k)[0] != '_']
            print(protected_keys, '!!!')
            if protected_keys:
                for key in protected_keys:
                    config_keys = self.config.keys()
                    if key in config_keys:
                        error = 'CAN NOT HAVE CONFIG THAT OVERWRITES CONSTANTS'
                        raise ValueError(error)
        else:
            return True
