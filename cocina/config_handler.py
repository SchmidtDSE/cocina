"""

Cocina Config Handler

This module provides the ConfigHandler class for managing project configuration
using YAML files, constants, and environment variables.

License: BSd 3-clause

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
from types import ModuleType
from dataclasses import dataclass, field
from cocina.constants import (
    COCINA_CONFIG_FILENAME, YAML_EXT_REGX, COCINA_NOT_FOUND,
    cocina_env_key, PY_EXT_REGX
)
from cocina.utils import (
    singleton, safe_join, dir_search, read_yaml, import_module_from_path,
    resolve_env_markers, resolve_markers
)


#
# HELPERS
#
def cocina_path(
        path: str,
        project_root: str,
        *subfolders: Union[str, int, float],
        config_name: Optional[str] = None,
        ext: Optional[str] = None,
        ext_regex: Optional[str] = None) -> str:
    """Get path of configuration file with flexible path resolution.

    Manages standard paths for a "cocina" project. Here is an example:

        ```python
        path = cocina_path(
            'a.b.c',
            '/path/to/my/project',
            'sub1',
            'sub2',
            ext='.yaml')

        print(path) # ==> /path/to/my/project/sub1/sub2/a/b/c.yaml
        ```

    Note:
        - <path> may or may not include the `project_root`
        - if <path> beings with "/" and does not contain <project_root> the
          the path remains unaltered.
        - otherwise:
            - allows for "dot-paths" (path.to.something) or file paths with "/"
        - <project_root> will be added unless the path begins with a "/"

    Examples with yaml ext and subfolders [config, args]:
        - a.b.job_name (loads config/args/a/b/job_name.yaml)
        - a/b/job_name (loads config/args/a/b/job_name.yaml)
        - a.b.job_name.yml (loads config/args/a/b/job_name.yml)
        - /a/b/job_name (loads /a/b/job_name - absolute path)

    Args:
        path: Path specification (dot or slash separated)
        project_root: Project root directory
        *subfolders: Additional subfolders to include in path
        config_name: FIX ME
        ext: File extension to add (default: None)
        ext_regex: Regular expression to match and extract extension from path

    Returns:
        Resolved file path
    """
    path = re.sub(f'^{project_root}/', '', path)
    if path[0] == '/':
        if config_name:
            pypath = Path(path)
            pycn = Path(config_name)
            path = str(pypath.parent / pypath.stem / pycn.stem)
            path += (pycn.suffix or pypath.suffix) 
        return path
    else:
        if ext_regex:
            match = re.search(ext_regex, path)
            if match:
                ext = match.group(0)
                path = re.sub(ext_regex, '', path)
            else:
                ext = ext or ''
        path = re.sub(r'\.', '/', path)
        parts = [project_root] + list(subfolders) + [path]
        if config_name:
            parts.append(config_name)
    return safe_join(*parts, ext=ext)


def _resolve_bind_args(
        project_root: str,
        args: Sequence[Union[str, dict]],
        values: dict) -> dict:
    """Merge ``bind()`` positional args (yaml paths and/or dicts) and kwargs into one dict.

    Handles the str/dict positional args the same way ``ConfigHandler.update`` does -
    a str is a path to a yaml file (relative to <project_root> unless absolute), a dict
    is merged directly. Unlike ``update``, a key provided by more than one source raises
    rather than letting the later source silently win: ``bind()`` already refuses to
    silently resolve a conflict across calls (the rebind guard in ``ConfigHandler.bind``),
    so the same key showing up twice within one call is the same footgun and gets the
    same treatment.

    Args:
        project_root: Project root directory, used to resolve string paths
        args: Positional args passed to ``bind()``
        values: Keyword args passed to ``bind()``

    Returns:
        Merged dict of key-value pairs to bind

    Raises:
        ValueError: If an arg is not a str or dict, or if a key is provided by
            more than one source (positional or keyword)
    """
    merged: dict = {}
    for arg in args:
        if isinstance(arg, dict):
            source = arg
        elif isinstance(arg, str):
            path = cocina_path(arg, project_root, ext_regex=YAML_EXT_REGX, ext='.yaml')
            source = read_yaml(path, safe=True)
        else:
            err = (
                'ch.bind arg must be either '
                'a string (path to a yaml file), or '
                'a dict (key-value pairs to bind)')
            raise ValueError(err)
        repeats = set(source) & set(merged)
        if repeats:
            raise ValueError(
                f'cocina: bind() got {sorted(repeats)} from more than one source')
        merged.update(source)
    repeats = set(values) & set(merged)
    if repeats:
        raise ValueError(
            f'cocina: bind() got {sorted(repeats)} from both *args and **values')
    merged.update(values)
    return merged


def get_project_root(
        project_root: Optional[str] = None,
        search_directory: Optional[str] = None) -> str:
    """Get project root directory.

    Searches for .cocina file in parent directories if project_root not provided.

    Args:
        project_root: Optional explicit project root path
        search_directory: Optional directory (or file path) to begin search at
                          otherwise use CWD
    Returns:
        Path to project root directory
    """
    if project_root is None:
        if search_directory:
            search_directory = Path(search_directory)
            if search_directory.is_file():
                search_directory = search_directory.parent
        project_root = dir_search(COCINA_CONFIG_FILENAME, directory=search_directory)
    return project_root


#
# DATA CLASSES
#
@dataclass
class CocinaConfig:
    """Dataclass for managing .cocina configuration.

    This dataclass holds all configuration settings loaded from the .cocina file
    that define how Cocina should locate and load configuration files.

    Usage:
        ```python
        cocina = CocinaConfig.init_for_project()
        config_path = cocina.config_folder + '/' + cocina.config_filename
        ```
    """
    config_folder: str
    args_config_folder: str
    config_filename: str
    jobs_folder: str
    constants_module_name: str
    default_env_key: str
    log_dir: Optional[str] = None
    constants_package_name: Optional[str] = None

    @classmethod
    def file_path(cls, project_root: Optional[str] = None) -> Self:
        """gets path for .cocina file

        Args:
            project_root: Optional explicit project root path

        Returns:
            str: project_root/.cocina
        """
        project_root = get_project_root(project_root)
        return f'{project_root}/{COCINA_CONFIG_FILENAME}'

    @classmethod
    def init_for_project(cls, project_root: Optional[str] = None) -> Self:
        """Create new CocinaConfig instance for project.

        Loads configuration from .cocina file in project root directory.
        If project_root is None, searches parent directories for .cocina file.

        Args:
            project_root: Optional explicit project root path

        Returns:
            CocinaConfig instance with loaded configuration
        """
        cocina_config = read_yaml(cls.file_path(project_root=project_root))
        return CocinaConfig(**cocina_config)


@dataclass
class ArgsKwargs:
    """Dataclass with args and kwargs properties.

    Used with ConfigArgs to allow accessing method arguments as
    ca.method_name.args and ca.method_name.kwargs.

    Usage:
        ```python
        args_kwargs = ArgsKwargs.init_from_value({'args': [1, 2], 'kwargs': {'key': 'value'}})
        some_method(*args_kwargs.args, **args_kwargs.kwargs)
        ```
    """
    args: Sequence[Any] = field(default_factory=list)
    kwargs: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def args_kwargs_from_value(value: Any) -> tuple[list, dict]:
        """Extract args and kwargs from a single value.

        Parsing rules:
        - If value is dict:
            - If keys are exclusively 'args' or 'kwargs': extract values from dict
            - Otherwise: args = [] and kwargs = value
        - If value is list/tuple: args = value, kwargs = {}
        - Otherwise: args = [value], kwargs = {}

        Args:
            value: Value to parse into args and kwargs

        Returns:
            Tuple containing (args_list, kwargs_dict)
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
        """Create ArgsKwargs from a value using args_kwargs_from_value.

        Args:
            value: Value to parse into ArgsKwargs instance

        Returns:
            ArgsKwargs instance with parsed args and kwargs
        """
        args, kwargs = cls.args_kwargs_from_value(value)
        return ArgsKwargs(args=args, kwargs=kwargs)


#
# CLASSES
#
@singleton
class ConfigHandler:
    """Handle project configuration using YAML files, constants, and environment variables.

    ConfigHandler provides a unified interface for managing configuration data across
    your project. It searches for a `.cocina` configuration file in parent directories,
    loads YAML configuration files, and optionally imports project constants.

    Requirements:
        Your project must have a `.cocina` file in the project root directory. This file
        contains cocina settings and is used to locate the project root and 
        configure how configuration files are loaded.

    Special Value Processing:
        ConfigHandler resolves `[[...]]` markers in configuration values:
        - `[[KEY]]`: another config key or a bound value (missing -> bare word + warning)
        - `[[ENV:VAR]]`: an environment variable (resolved once, at load)
        - `[[COCINA:ENV]]`: the current environment name (resolved once, at load)

        `[[KEY]]` markers stay literal in the template and are re-resolved from
        `template + bindings` on every `bind()`. Escape with a backslash for a
        literal bracket: `\\[[Page]]` renders as `[[Page]]`.

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
        ch.add_job_config('/path/to/job.py')               # Load job config
        ch.add_job_config('/path/to/job.py', version='v2') # Versioned job config
        
        # With constants module
        ch = ConfigHandler('/path/to/my/module')
        ```

    Configuration Loading:
        1. Searches parent directories for `.cocina` file (project root)
        2. Reads `.cocina` configuration settings
        3. Loads main config file (default: config/config.yaml)
        4. Optionally loads environment-specific config based on cocina.ENV_NAME
        5. Imports constants module if module_path provided

    Priority Order (highest to lowest):
        1. Constants from imported module
        2. Configuration values from YAML files
        3. Default values provided to get() method

    Args:
        package_locator: Optional string used to help determine the location of a
            "constants.py" file:
            - None: use cocina.constants_package_name
            - String containing "/":  path to a file withing the same package
              as the constants.py file
            - String NOT containing "/": the name of the package containg the
              constants.py file

    Raises:
        ValueError: If configuration attempts to overwrite constants or .cocina not found
        KeyError: If attempting to access non-existent configuration key without default
    """
    def __init__(self,
            search_directory: Optional[str] = None,
            package_locator: Optional[str] = None,
            constants: Optional[ModuleType] = None) -> None:
        """Initialize ConfigHandler.
        
        Args:
            search_directory: Optional search_directory for finding .cocina config file
            package_locator: Optional string used to help determine the location of a
                "constants.py" file:
                - None: use cocina.constants_package_name
                - String containing "/":  path to a file withing the same package
                  as the constants.py file
                - String NOT containing "/": the name of the package containg the
                  constants.py file
            constants: Optional ModuleType. if provided <package_locator> ignored,
                and ch.constants = <constants>
        """
        self._bindings: dict = {}
        self._unresolved: list[str] = []
        self.project_root = get_project_root(search_directory=search_directory)
        self.cocina = CocinaConfig.init_for_project(self.project_root)
        self.constants = constants or self._import_constants(package_locator)
        raw_config, self.environment_name = self._config_and_environment()
        self.template = resolve_env_markers(raw_config, self.environment_name)
        self._check_protected_keys()
        self._resolve()

    def update(self, *args: Union[str, dict], **kwargs) -> None:
        """Replace the config template with a newly merged copy, then re-resolve.

        Reads all update inputs (yaml paths and/or dicts) plus keyword arguments,
        merges them into a copy of ``self.template`` using shallow ``dict.update``
        precedence, freezes construction-time env markers in the newly admitted
        values, and re-derives ``self.config`` with the existing bindings. A binding
        still wins when an update defines the same key.

        Args:
            *args: str (path to a yaml file, absolute or relative to project root)
                and/or dict of key-value pairs to merge.
            **kwargs: Key-value pairs to merge.

        Raises:
            ValueError: If an argument is not a str or dict, or the merged config
                would overwrite a protected constant.
        """
        updates: dict = {}
        for arg in args:
            if isinstance(arg, dict):
                updates.update(arg)
            elif isinstance(arg, str):
                path = cocina_path(
                    arg, self.project_root, ext_regex=YAML_EXT_REGX, ext='.yaml')
                updates.update(read_yaml(path, safe=True))
            else:
                err = (
                    'ch.update arg must be either '
                    'a string (path to config-file), or '
                    'a dict (key-value pairs to update config)')
                raise ValueError(err)
        updates.update(kwargs)
        admitted = resolve_env_markers(updates, self.environment_name)
        new_template = {**self.template, **admitted}
        self.template = new_template
        self._check_protected_keys()
        self._resolve()

    def bind(self, *args: Union[str, dict], rebind: bool = False, **values: Any) -> None:
        """Bind runtime values and re-resolve the config from the pristine template.

        `[[KEY]]` markers with no bound (or config) value are left as their bare word
        and reported by ``unresolved``; bind as values become known. Because every
        bind re-resolves from ``self.template`` rather than editing a substituted
        string, changing a bound key is possible with ``rebind=True``.

        Usage:
            ```python
            ch.bind(MODEL_NAME='owl', MODEL_VERSION='v4')
            ch.bind('cards/owl-v4.yaml')
            ch.bind(MODEL_NAME='birdnet', rebind=True)
            ```

        Args:
            *args: Same as ``update`` - str (path to yaml file) and/or dict.
            rebind: Allow changing an already-bound key to a different value.
            **values: Runtime key-value pairs to bind. A key given by more than one
                source in a single call raises rather than silently picking one.

        Raises:
            ValueError: If an arg is not a str or dict, a key is provided by more than
                one source in this call, or a key is already bound to a different value
                and ``rebind`` is False.
        """
        merged = _resolve_bind_args(self.project_root, args, values)
        if not rebind:
            conflicts = {
                k for k, v in merged.items()
                if k in self._bindings and self._bindings[k] != v}
            if conflicts:
                raise ValueError(
                    f'cocina: keys already bound, pass rebind=True to change: '
                    f'{sorted(conflicts)}')
        self._bindings.update(merged)
        self._resolve()

    def unresolved(self) -> list[str]:
        """`[[KEY]]` markers unresolved in the current config view (non-warning).

        Reports both direct missing references and residual markers left by the
        single-pass (non-chaining) boundary. Safe for a pre-run guard,
        e.g. ``assert not ch.unresolved()``.

        Returns:
            Order-preserving, de-duplicated list of unresolved marker strings.
        """
        return list(self._unresolved)

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
        value = getattr(self.constants, key, COCINA_NOT_FOUND)
        if value == COCINA_NOT_FOUND:
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
        value = self.get(key, COCINA_NOT_FOUND)
        if value == COCINA_NOT_FOUND:
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
                'ConfigHandler:\n'
                f'- constants: {self.constants}\n'
                f'- config: {self.config}')
        return rep

    #
    # INTERNAL
    #
    def _import_constants(self,
            package_locator: Optional[str] = None) -> Union[ModuleType, None]:
        """Import constants module if it exists.
        
        Args:
            package_locator: Optional string used to help determine the location of a
                "constants.py" file:
                - None: use cocina.constants_package_name
                - String containing "/":  path to a file withing the same package
                  as the constants.py file
                - String NOT containing "/": the name of the package containg the
                  constants.py file

        Returns:
            Imported constants module or None
        """
        if package_locator is None:
            package_name = self.cocina.constants_package_name
        elif ('/' in package_locator):
            locator_path = str(Path(package_locator).resolve())
            package_name = re.sub(f'{self.project_root}/', '', locator_path).split('/', 1)[0]
        else:
            package_name = package_locator
        constants_module = None
        if package_name:
            dot_path = f'{package_name}.{self.cocina.constants_module_name}'
            try:
                constants_module = importlib.import_module(dot_path)
            except ImportError as e:
                pass
        return constants_module


    def _config_and_environment(self) -> tuple[dict, Optional[str]]:
        """Load configuration, adding environment-specific config if it exists.
        
        Returns:
            Tuple containing config dictionary and environment name
        """
        config_path = cocina_path(
            self.cocina.config_filename,
            self.project_root,
            self.cocina.config_folder,
            ext_regex=YAML_EXT_REGX,
            ext='.yaml')
        config = read_yaml(config_path, safe=True)
        default_env = config.pop(self.cocina.default_env_key, None)
        environment_name = os.environ.get(cocina_env_key, default_env)
        if environment_name:
            env_path = cocina_path(
                self.project_root,
                self.cocina.config_folder,
                environment_name,
                ext_regex=YAML_EXT_REGX,
                ext='.yaml')
            config.update(read_yaml(env_path, safe=True))
        return config, environment_name

    def _binding_source(self) -> dict:
        """Lookup for `[[KEY]]` resolution: string-valued template scalars, then bindings.

        Bindings win on conflict (decision 8). Scalars are raw top-level string config
        values from the pristine template, never taken from a previously resolved view.
        """
        scalars = {k: v for k, v in self.template.items() if isinstance(v, str)}
        return {**scalars, **self._bindings}

    def _resolve(self) -> None:
        """Recompute ``self.config`` and ``self._unresolved`` from template + bindings."""
        self.config, self._unresolved = resolve_markers(
            self.template, self._binding_source())

    def _check_protected_keys(self) -> None:
        """Ensure user's config files do not overwrite constants.py values.

        Raises:
            ValueError: If the config template defines a key protected by constants
        """
        if self.constants:
            protected_keys = [k for k in dir(self.constants) if str(k)[0] != '_']
            for key in protected_keys:
                if key in self.template:
                    raise ValueError('Configuration cannot overwrite constants')


class ConfigArgs:
    """Manage job-specific configuration and method arguments.

    ConfigArgs provides a unified interface for loading job configuration files
    and accessing method arguments in a structured way. It integrates with
    ConfigHandler to provide configuration management for job execution.

    The class performs the following operations:
    1. Sets up ConfigHandler for configuration management
    2. Loads argument configuration from specified path
    3. Resolves `[[...]]` markers in the arg-sections through an instance-local
       `args_template`, combined with the shared handler's config and bindings
    4. Creates ArgsKwargs attributes for each method in the config

    Path Resolution:
        - job_name: loads config/args/job_name.yaml
        - a.b.job_name: loads config/args/a/b/job_name.yaml
        - a/b/job_name: loads config/args/a/b/job_name.yaml
        - /a/b/job_name: loads /a/b/job_name (absolute path)

    Warning:
        - Config names cannot include "." except for YAML extension

    Usage:
        ```python
        ca = ConfigArgs('my_job')
        some_method(*ca.some_method.args, **ca.some_method.kwargs)

        # Import and run the job module
        job_module = ca.import_job_module()
        job_module.run(*ca.run.args, **ca.run.kwargs)
        ```
    """
    def __init__(self,
            config_path: Optional[str] = None,
            user_config: Optional[dict] = None,
            config_name: Optional[dict] = None,
            config_handler: Optional[ConfigHandler] = None) -> None:
        """Initialize ConfigArgs.

        Args:
            config_path: 
                Path to job configuration file (relative to project_root/config/args/)
            user_config: Optional dictionary of user configuration overrides
            config_name: 
                If non-null assume config_path returns folder and load the 
                file <config_name>.yaml
            config_handler: Optional existing ConfigHandler instance to use
        """
        # set/load config_handler
        if config_handler:
            self.config_handler = config_handler
        else:
            self.config_handler = ConfigHandler()
        job, args_config, config = self._args_data(config_path, user_config, config_name=config_name)

        self.config_handler.update(config)
        self.args_template = resolve_env_markers(
            args_config, self.config_handler.environment_name)
        self.args_config, self._unresolved = resolve_markers(
            self.args_template, self.config_handler._binding_source())
        self.property_names = list(self.args_config.keys())
        self.job_path = cocina_path(
            re.sub(YAML_EXT_REGX, '', job or config_path),
            self.config_handler.project_root,
            self.config_handler.cocina.jobs_folder,
            ext='.py',
            ext_regex=PY_EXT_REGX)
        self._set_arg_kwargs()


    def import_job_module(self) -> Any:
        """Helper to import job module.

        Usage:
            ```python
            ca = ConfigArgs(job)
            job_module = ca.import_job_module()
            ```

        Returns:
            Imported job module object
        """
        return import_module_from_path(self.job_path)

    def bind(self, *args: Union[str, dict], rebind: bool = False, **values: Any) -> "ConfigArgs":
        """Bind runtime values into the shared config and this job's arg-sections.

        Delegates to ``ConfigHandler.bind`` (which re-resolves the shared config from
        its pristine template), then re-resolves this instance's arg-sections from
        ``self.args_template`` and rebuilds the ``ca.<section>.args`` / ``.kwargs``
        wrappers. Only this instance's wrappers refresh.

        Usage:
            ```python
            ca.bind(MODEL_NAME=card.model_name, MODEL_VERSION=card.model_version)
            ca.bind('cards/owl-v4.yaml')
            ca.bind(MODEL_NAME='birdnet', rebind=True)
            ```

        Args:
            *args: Same as ``ConfigHandler.bind`` - str (path to yaml file) and/or dict.
            rebind: Allow changing an already-bound key to a different value.
            **values: Runtime key-value pairs to bind.

        Returns:
            self, for chaining

        Raises:
            ValueError: If an arg is not a str or dict, a key is provided by more than
                one source in this call, or a key is already bound to a different value
                and ``rebind`` is False.
        """
        # _resolve_bind_args normalizes here; ConfigHandler.bind re-normalizes the merged kwargs (idempotent, intentional)
        merged = _resolve_bind_args(self.config_handler.project_root, args, values)
        self.config_handler.bind(rebind=rebind, **merged)
        self.args_config, self._unresolved = resolve_markers(
            self.args_template, self.config_handler._binding_source())
        self._set_arg_kwargs()
        return self

    def unresolved(self) -> list[str]:
        """`[[KEY]]` markers unresolved in the shared config or this job's arg-sections.

        Unions the handler's unresolved markers with this instance's, preserving
        first-seen order and dropping duplicates. Non-warning.

        Returns:
            Order-preserving, de-duplicated list of unresolved marker strings.
        """
        seen: list[str] = []
        for marker in list(self.config_handler.unresolved()) + list(self._unresolved):
            if marker not in seen:
                seen.append(marker)
        return seen

    def get(self, key: str, default: Any = None) -> Any:
        """get properties of config_handler and config args as attributes with default fallback.

        Provides attribute-style access to configuration values. First checks
        if the key exists in the config_handler, then falls back to the
        current object's attributes.

        Args:
            key: Attribute name to access

        Returns:
            Value of the requested attribute

        Usage:
            ```python
            ca = ConfigArgs('job_name')
            value = ca.some_config_key  # Access config value as attribute
            ```
        """
        if key in self.config_handler:
            return getattr(self.config_handler, key, default)
        else:
            return getattr(self, key, default)

    def __getattr__(self, key: str) -> Any:
        """Access properties of config_handler and config args as attributes.

        Provides attribute-style access to configuration values. First checks
        if the key exists in the config_handler, then falls back to the
        current object's attributes.

        Args:
            key: Attribute name to access

        Returns:
            Value of the requested attribute

        Usage:
            ```python
            ca = ConfigArgs('job_name')
            value = ca.some_config_key  # Access config value as attribute
            ```
        """
        if key in self.config_handler:
            return getattr(self.config_handler, key)
        else:
            raise AttributeError(f'{key} not found in config_handler or config_args (ConfigArgs.__getattr__)')

    def __repr__(self) -> str:
        """Return string representation of ConfigHandler."""
        rep = 'ConfigArgs:\n'
        for n in self.property_names:
            rep += f'- {n}: {getattr(self, n)}\n'
        return rep

    #
    # INTERNAL
    #
    def _args_data(
            self,
            config_path: str, 
            user_config: Union[dict, None],
            config_name: Optional[str] = None) -> tuple[dict, Union[str, None], dict]:
        """
        FIX  ME
        """
        args_config_path = cocina_path(
            config_path,
            self.config_handler.project_root,
            self.config_handler.cocina.config_folder,
            self.config_handler.cocina.args_config_folder,
            config_name=config_name,
            ext='.yaml',
            ext_regex=YAML_EXT_REGX)
        parent = Path(args_config_path).parent
        if config_name:
            parent_config_path = (parent.parent / 'config.yaml')
        else:
            parent_config_path = (parent / 'config.yaml')

        if (parent.name != 'args') and parent_config_path.is_file():
            parent_config = read_yaml(str(parent_config_path))
            parent_env = parent_config.pop('env', {})
        else:
            parent_config = {}
            parent_env = {}
        try:
            args_config = read_yaml(args_config_path)
            # pop special values
            job = args_config.pop('job', None)
            config = args_config.pop('config', {})
            env = args_config.pop('env', {})
            config = {**parent_config, **config}
            env = {**parent_env, **env}
            if self.config_handler.environment_name:
                env = env.pop(self.config_handler.environment_name, {})
                config.update(env)
            if user_config:
                config.update(user_config)
        except Exception as e:
            job, args_config, config = None, {}, {}
        return job, args_config, config

    def _set_arg_kwargs(self) -> None:
        """Set ArgsKwargs attributes for each property in args_config.

        Creates dynamic attributes on the instance for each key in args_config,
        converting values to ArgsKwargs instances for structured access to
        method arguments and keyword arguments.

        Usage:
            >>> config_args = ConfigArgs('job1')
            >>> config_args._set_arg_kwargs()  # Sets attributes from args_config
            >>> args = config_args.method_name.args
            >>> kwargs = config_args.method_name.kwargs
        """
        for k, v in self.args_config.items():
            setattr(self, k, ArgsKwargs.init_from_value(v))

