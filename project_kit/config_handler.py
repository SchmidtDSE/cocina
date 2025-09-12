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
import re
from pathlib import Path
from typing import Any, Optional, Union

from project_kit import constants as c
from project_kit import utils


#
# PUBLIC
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
        ch.update(new_setting='value')
        
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
        self.project_root = utils.dir_search(c.PKIT_CONFIG_FILENAME)
        self.pkit_config = utils.read_yaml(f'{self.project_root}/{c.PKIT_CONFIG_FILENAME}')
        self.constants = self._import_constants(module_path)
        self.config = self._load_config()
        self._check_protected_keys()

    def update(self, **kwargs) -> None:
        """Update configuration with keyword arguments.
        
        Args:
            **kwargs: Key-value pairs to update configuration with
        """
        self.config.update(kwargs)



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
            try:
                constants_module = importlib.import_module(f'{module_name}.{self.pkit_config["constants_module_name"]}')
            except ImportError:
                pass
        return constants_module


    def _load_config(self) -> dict:
        """Load configuration, adding environment-specific config if it exists.
        
        Returns:
            Dictionary containing merged configuration data
        """
        config_dir = f'{self.project_root}/{self.pkit_config["config_folder"]}'
        config = utils.read_yaml(f'{config_dir}/{self.pkit_config["config_filename"]}')
        default_env = config.pop(self.pkit_config['default_env_key'], None)
        env = os.environ.get(self.pkit_config['project_kit_env_var_name'], default_env)
        if env:
            config.update(utils.read_yaml(f'{config_dir}/{env}.yaml'))
        return config


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
