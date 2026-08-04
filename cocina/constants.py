"""

Cocina Constants

This module contains constant values used throughout the Cocina package.

License: BSd 3-clause

"""
#
# CONSTANTS
#

# cocina:core
COCINA_CONFIG_FILENAME: str = '.cocina'
COCINA_NOT_FOUND: str = '__cocina_OBJECT_NOT_FOUND'

# cocina:cli
COCINA_CLI_DEFAULT_HEADER: str = 'cocina_job'

# REGEX
PY_EXT_REGX: str = r'\.py$'
YAML_EXT_REGX: str = r'\.(yaml|yml)$'
KEY_STR_REGEX: str = r'[a-zA-Z][a-zA-Z0-9_-]*'

# icons
ICON_START = "🚀"
ICON_FAILED = "❌"
ICON_SUCCESS = "✅"

# config/args keyed-identifiers
# - auto-update config/args with env
ENVIRONMENT_KEYED_IDENTIFIER: str = r'\[\[COCINA:ENV\]\]'

# - deferred (runtime-bound) values: left intact by process_values,
#   resolved later by ConfigHandler.bind(**values) / ConfigArgs.bind(**values)
DEFERRED_MARKER_PREFIX: str = '{{COCINA:'
DEFERRED_MARKER_SUFFIX: str = '}}'
DEFERRED_KEYED_IDENTIFIER: str = r'\{\{COCINA:' + KEY_STR_REGEX + r'\}\}'

# environment variables
# - env-key to store "env-name" to manage environment-specific configs/args
cocina_env_key = "cocina.ENV_KEY"
# - env-key to store path to current log file
cocina_log_path_key = "cocina.LOG_PATH_KEY"

