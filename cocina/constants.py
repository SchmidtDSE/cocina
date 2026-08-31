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

# unified [[...]] marker grammar
# - one bracket, an optional NAMESPACE: prefix inside [[...]]
# - MARKER_REGEX captures an optional leading backslash escape (group 1)
#   and the inner expression (group 2)
MARKER_REGEX: str = r'(\\?)\[\[([^\[\]]+)\]\]'

# environment-variable names for [[ENV:VAR]] (dotted + hyphenated allowed:
# the project already reads the dotted `cocina.ENV_KEY`)
ENV_VAR_REGEX: str = r'[A-Za-z_][A-Za-z0-9_.-]*'

# reserved namespaces: ENV (os.environ) and COCINA (cocina-internal;
# currently the single member COCINA:ENV, the environment *name*)
COCINA_ENV_MARKER: str = 'COCINA:ENV'
ENV_NAMESPACE_PREFIX: str = 'ENV:'
COCINA_NAMESPACE_PREFIX: str = 'COCINA:'

# environment variables
# - env-key to store "env-name" to manage environment-specific configs/args
cocina_env_key = "cocina.ENV_KEY"
# - env-key to store path to current log file
cocina_log_path_key = "cocina.LOG_PATH_KEY"

