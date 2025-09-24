"""

Project Kit Constants

This module contains constant values used throughout the Project Kit package.

License: CC-BY-4.0

"""
#
# CONSTANTS
#

# pkit:core
PKIT_CONFIG_FILENAME: str = '.pkit'
PKIT_NOT_FOUND: str = '__PKIT_OBJECT_NOT_FOUND'

# pkit:cli
PKIT_CLI_DEFAULT_HEADER: str = 'pkit_job'

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
ENVIRONMENT_KEYED_IDENTIFIER: str = r'\[\[PKIT:ENV\]\]'

# environment variables
# - env-key to store "env-name" to manage environment-specific configs/args
project_kit_env_key = "PROJECT_KIT.ENV_KEY"
# - env-key to store path to current log file
project_kit_log_path_key = "PROJECT_KIT.LOG_PATH_KEY"

