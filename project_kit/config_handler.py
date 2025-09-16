"""

Project Kit Config Handler

This module provides the ConfigHandler class for managing project configuration
using YAML files, constants, and environment variables.

License: CC-BY-4.0

"""
#
# IMPORTS
#
import importlib
import os
import sys
import re
from pathlib import Path
from typing import Any, Optional, Union, Self, Sequence
from dataclasses import dataclass, field


from project_kit import constants as c
from project_kit import utils


#
# UTILS
#
def load_job_module(module_path, project_root=None, pkit_config=None):
    """Dynamically load a job module by file path.

    Loads and executes a Python module for job processing. If a relative path is provided,
    it constructs the full path using project root and jobs folder configuration.

    Args:
        module_path: Path to the Python module file (absolute or relative to jobs folder)
        project_root: Optional project root path (auto-detected if None)
        pkit_config: Optional pkit configuration dict (auto-loaded if None)

    Returns:
        module: The loaded and executed Python module

    Raises:
        ImportError: If module cannot be loaded or executed
        FileNotFoundError: If module file cannot be found
    """
    if module_path[0] != '/':
        project_root, pkit_config = _project_root_and_pkit_config(project_root, pkit_config)
        parts = [
            project_root,
            pkit_config['jobs_folder'],
            re.sub(c.PY_EXT_REGX, '', module_path)]
        module_path = f'{"/".join(parts)}.py'
    spec = importlib.util.spec_from_file_location("module.name", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["module.name"] = module
    spec.loader.exec_module(module)
    return module


#
# MAIN
#
class ConfigHandler:
    """Handle project configuration using YAML files, constants, and environment variables.

    ConfigHandler provides a unified interface for managing configuration data across
    your project. It searches for a `.pkit` configuration file in parent directories,
    loads YAML configuration files, and optionally imports project constants.

    Requirements:
        Your project must have a `.pkit` file in the project root directory. This file
        contains project_kit settings and is used to locate the project root and 
        configure how configuration files are loaded.

    Usage:
        ```python
        # Basic usage
        ch = ConfigHandler()
        
        # Access configuration values
        db_host = ch.get('database_host', 'localhost')  # With default
        api_key = ch['api_key']                         # Direct access (raises KeyError if not found)
        log_level = ch.log_level                        # Attribute access
        
        # Check if key exists
        if 'optional_setting' in ch:
            value = ch.optional_setting
        
        # Update configuration
        ch.update(new_setting='value')                    # Keyword arguments
        ch.update({'key': 'value'})                       # Dictionary merge
        ch.update('config/extra.yaml')                    # Load from YAML file

        # Job-specific configuration
        ch.add_job_config('/path/to/job.py')              # Load job config
        ch.add_job_config('/path/to/job.py', version='v2') # Versioned job config
        
        # With constants module
        ch = ConfigHandler('/path/to/my/module')
        ```

    Configuration Loading:
        1. Searches parent directories for `.pkit` file (project root)
        2. Reads `.pkit` configuration settings
        3. Loads main config file (default: config/config.yaml)
        4. Optionally loads environment-specific config based on PROJECT_KIT.ENV_NAME
        5. Imports constants module if module_path provided

    Priority Order (highest to lowest):
        1. Constants from imported module
        2. Configuration values from YAML files
        3. Default values provided to get() method

    Args:
        module_path: Optional path to module containing constants to import

    Raises:
        ValueError: If configuration attempts to overwrite constants or .pkit not found
        KeyError: If attempting to access non-existent configuration key without default
    """
    def __init__(self, module_path: Optional[str] = None) -> None:
        """Initialize ConfigHandler.
        
        Args:
            module_path: Optional path to module for constants import
        """
        self.project_root, self.pkit_config = _project_root_and_pkit_config()
        self.constants = self._import_constants(module_path)
        self.config, self.environment_name = self._config_and_environment()
        self.config = self.process_values(self.config)
        self._check_protected_keys()

    def update(self, *args: Union[str, dict], **kwargs) -> None:
        """Update configuration with YAML files, dictionaries, or keyword arguments.

        Supports multiple update methods: loading from YAML files (via string paths),
        merging dictionary data, or updating with keyword arguments. All updates
        are validated against protected constants.

        Args:
            *args: Variable arguments supporting:
                - str: Path to YAML file to load and merge (absolute or relative to project root)
                - dict: Dictionary of key-value pairs to merge into configuration
            **kwargs: Key-value pairs to update configuration with

        Raises:
            ValueError: If arguments are invalid type or configuration conflicts with constants
            FileNotFoundError: If YAML file path cannot be found
        """
        for arg in args:
            if isinstance(arg, dict):
                self.config.update(arg)
            elif isinstance(arg, str):
                # if str starts with / let it be the full path
                # else assume starts from project_root
                # TODO: MAKE SURE THIS LOGIC IS RIGHT under /config/?
                # TODO: READ_YAML check for ext?
                if arg.startswith('/'):
                    path = arg
                else:
                    path = f'{self.project_root}/{arg}'
                yaml_config = utils.read_yaml(path, safe=True)
                self.config.update(yaml_config)
            else:
                err = (
                    'ch.update arg must be either '
                    'a string (path to config-file), or '
                    'a dict (key-value pairs to update config)')
                raise ValueError(err)
        self.config.update(kwargs)
        self.config = self.process_values(self.config)
        self._check_protected_keys()

    def process_values(self, config: dict):
        """ given a configuration dict replace all values that are
        strings whose VALUE is a key in CONSTANTS or CONFIG of CH
        """
        return utils.replace_dictionary_values(config, self.config)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with default fallback.

        Usage:
            ```python
            c.get('some_key')
            ```

        Note: If value is all uppercase and is a key in config handler,
        returns that value instead (recursive lookup).

        Args:
            key: Key to access
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        value = getattr(self.constants, key, c.PKIT_NOT_FOUND)
        if value == c.PKIT_NOT_FOUND:
            value = self.config.get(key, default)
        if isinstance(value, str) and value.isupper() and (value in self):
            value = self[value]
        return value

    def __contains__(self, key) -> bool:
        """Check if key exists in configuration or constants.
        
        Usage:
            ```python
            'key' in c
            ```

        Args:
            key: Key to check

        Returns:
            True if key exists, False otherwise
        """
        if isinstance(key, str):
            contains = key in self.config
            if not contains:
                contains = hasattr(self.constants, key)
            return contains
        return False

    def __getitem__(self, key: str) -> Any:
        """Get configuration value (raises error if key does not exist).
        
        Usage:
            ```python
            c['some_key']
            ```

        Args:
            key: Key to access

        Returns:
            Configuration value

        Raises:
            KeyError: If key not found in configuration or constants
        """
        value = self.get(key, c.PKIT_NOT_FOUND)
        if value == c.PKIT_NOT_FOUND:
            raise KeyError(f'{key} not found in config, or constants')
        else:
            return value

    def __getattr__(self, key: str) -> Any:
        """Get configuration value as attribute.
        
        Usage:
            ```python
            c.some_key
            ```

        Args:
            key: Key to access

        Returns:
            Configuration value
        """
        return self.__getitem__(key)

    def __repr__(self) -> str:
        """Return string representation of ConfigHandler."""
        rep = (
                f'ConfigHandler:\\n'
                f'- constants: {self.constants}\\n'
                f'- config: {self.config}')
        return rep

    #
    # INTERNAL
    #
    def _import_constants(self, module_path: Optional[str]):
        """Import constants module if it exists.
        
        Args:
            module_path: Path to module containing constants
            
        Returns:
            Imported constants module or None
        """
        constants_module = None
        if module_path:
            module_path = str(Path(module_path).resolve())
            module_name = re.sub(f'{self.project_root}/', '', module_path).split('/', 1)[0]
            print('...', module_path, module_name, '---')
            try:
                constants_module = importlib.import_module(f'{module_name}.{self.pkit_config["constants_module_name"]}')
            except ImportError:
                pass
        return constants_module

    def _config_and_environment(self) -> dict:
        """Load configuration, adding environment-specific config if it exists.
        
        Returns:
            Dictionary containing merged configuration data
        """
        config_dir = f'{self.project_root}/{self.pkit_config["config_folder"]}'
        config = utils.read_yaml(f'{config_dir}/{self.pkit_config["config_filename"]}', safe=True)
        default_env = config.pop(self.pkit_config['default_env_key'], None)
        environment_name = os.environ.get(self.pkit_config['project_kit_env_var_name'], default_env)
        if environment_name:
            config.update(utils.read_yaml(f'{config_dir}/{environment_name}.yaml', safe=True))
        return config, environment_name

    def _check_protected_keys(self) -> None:
        """Ensure user's config files do not overwrite constants.py values.
        
        Raises:
            ValueError: If configuration attempts to overwrite constants
        """
        if self.constants:
            protected_keys = dir(self.constants)
            protected_keys = [k for k in protected_keys if str(k)[0] != '_']
            if protected_keys:
                for key in protected_keys:
                    config_keys = self.config.keys()
                    if key in config_keys:
                        raise ValueError('Configuration cannot overwrite constants')



#
# MAIN
#
@dataclass
class ArgsKwargs:
    """
    - dataclass with args, kwargs properties.
    - used with ConfigArgs to allow from ca.method_name.(args|kwargs)
    """
    args: Sequence[Any] = field(default_factory=list)
    kwargs: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def args_kwargs_from_value(value: Any) -> tuple[list, dict]:
        """
        static method that takes a single value and extracts it into
        args and kwargs.

        - if value is dict:
            - if keys that are exclusively args or kwargs extract values from dict
            - otherwise args = [] and kwargs = value
        - else if value is list/tuple, args = value, kwargs = {}
        - else args = [value], kwargs = {}
        """
        if isinstance(value, dict):
            keys_set = set(value.keys())
            if keys_set.issubset(set(['args', 'kwargs'])):
                args = value.get('args', [])
                kwargs = value.get('kwargs', {})
            else:
                args = []
                kwargs = value
        elif isinstance(value, (list,tuple)):
            args = value
            kwargs = {}
        else:
            args = [value]
            kwargs = {}
        return args, kwargs

    @classmethod
    def init_from_value(cls, value: Any) -> Self:
        """
        creates a ArgsKwargs from a value using `args_kwargs_from_value`
        """
        args, kwargs = cls.args_kwargs_from_value(value)
        return ArgsKwargs(args=args, kwargs=kwargs)


class ConfigArgs:
    """

    1. sets ConfigHandler (ch)

    2. loads a arg-config-dict from path/do-path

        arg_config = job_name (loads config/args/job_name)
        arg_config = a.b.job_name (loads config/args/a/b/job_name.yaml)
        arg_config = a/b/job_name (loads config/args/a/b/job_name.yaml)
        arg_config = /a/b/job_name (loads /a/b/job_name)
        ** yaml ext or none is fine
        ** leading / => full path otherwise project_root/config/args/
        ** arg_config names can not include a "." except if yaml ext

    3. process arg_config
        - update ch with config/env from arg_config yaml
        - replace values that are properties in ch

    4. for all "property_names" (names of methods) in arg_config
       set corresponding ArgsKwargs instance values


    Usage:

        ```python
        ca = ConfigArgs()
        some_method(*ca.some_method.args, **ca.some_method.kwargs)
        ```
    """
    def __init__(self,
            config_path: Optional[str] = None,
            user_config: Optional[dict] = None,
            config_handler: Optional[ConfigHandler] =None) -> None:
        """Initialize ConfigHandler.

        Args:
            module_path: Optional path to module for constants import
        """
        if config_handler:
            self.config_handler = config_handler
        else:
            self.config_handler = ConfigHandler()
        args_config = utils.read_yaml(self._args_config_path(config_path))
        config = args_config.pop('CONFIG', {})
        env = args_config.pop('ENV', {})
        if self.config_handler.environment_name:
            env = env.pop(self.config_handler.environment_name, {})
            config.update(env)
        if user_config:
            config.update(user_config)
        self.config_handler.update(config)
        # 3. process values before returning
        self.args_config = self.config_handler.process_values(args_config)
        self.property_names = list(self.args_config.keys())
        self._set_arg_kwargs()

    def __repr__(self) -> str:
        """Return string representation of ConfigHandler."""
        rep = 'ConfigArgs:\n'
        for n in self.property_names:
            rep += f'- {n}: {getattr(self, n)}\n'
        return rep

    #
    # INTERNAL
    #
    def _set_arg_kwargs(self):
        for k, v in self.args_config.items():
            setattr(self, k, ArgsKwargs.init_from_value(v))

    def _args_config_path(self, path):
        """
        get path of args file
        - a.b.custom_job (loads config/args/a/b/custom_job.yaml)
        - a/b/custom_job (loads config/args/a/b/custom_job.yaml)
        - a.b.custom_job.yml (loads config/args/a/b/custom_job.yml)
        - /a/b/custom_job (loads /a/b/custom_job)
        """
        if path[0] == '/':
            return path
        else:
            match = re.search(c.YAML_EXT_REGX, path)
            if match:
                ext = match.group(0)
                path = re.sub(c.YAML_EXT_REGX, '', path)
            else:
                ext = '.yaml'
            path = re.sub(r'\.', '/', path)
        return utils.safe_join(
            self.config_handler.project_root,
            self.config_handler.pkit_config['config_folder'],
            self.config_handler.pkit_config['args_config_folder'],
            path,
            ext=ext)


        path = Path(path)
        ext = path.suffix
        if ext not in ['', 'yml', 'yaml']:
            raise ValueError(f"ext must be in ['', '.yml', '.yaml']: ext={ext}")
        base = path.parent / path.stem
        base = re.sub(r'\.', '/', base)
        return base + ext



#
# INTERNAL
#
def _project_root_and_pkit_config(project_root=None, pkit_config=None):
    """(if necessary) get project_root and load pkit_config"""
    if project_root is None:
        project_root = utils.dir_search(c.PKIT_CONFIG_FILENAME)
    if pkit_config is None:
        pkit_config = utils.read_yaml(f'{project_root}/{c.PKIT_CONFIG_FILENAME}')
    return project_root, pkit_config
