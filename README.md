# Project Kit

Project Kit (PKIT) is a collection of tools for building out python projects. PKIT contains:

1. a config_handler: used for mangaing constants and configuation for python projects
2. a job runner: used for cleanly executing a sequence of script steps
3. a config_interface: decorator that passes args in configuration files to python methods
4. utilities such as timers and custom loggers

## Table of Contents

- [Install/Requirements](#installrequirements)
- [Quick Start](#quick-start)
- [Components](#components)
  - [Config Handler](#config-handler)
  - [Job Runner](#job-runner)
  - [Config Interface](#config-interface)
  - [Utilities](#utilities)
- [.pkit Configuration](#pkit-configuration)
- [Documentation](#documentation)
- [Style Guide](#style-guide)

---

## INSTALL/REQUIREMENTS

Requirements are managed through a [Pixi](https://pixi.sh/latest) "project" (similar to a conda environment). After pixi is installed use `pixi run <cmd>` to ensure the correct project is being used. For example,

```bash
# lauch jupyter
pixi run jupyter lab .

# run a script
pixi run python scripts/hello_world.py
```

The first time `pixi run` is executed the project will be installed (note this means the first run will be a bit slower). Any changes to the project will be updated on the subsequent `pixi run`.  It is unnecessary, but you can run `pixi install` after changes - this will update your local environment, so that it does not need to be updated on the next `pixi run`.

Note, the repo's `pyproject.toml`, and `pixi.lock` files ensure `pixi run` will just work. No need to recreate an environment. Additionally, the `pyproject.toml` file includes `project_kit = { path = ".", editable = true }`. This line is equivalent to `pip install -e .`, so there is no need to pip install this module.

The project was initially created using a `package_names.txt` and the following steps. Note that this should **NOT** be re-run as it will create a new project (potentially changing package versions).

```bash
#
# IMPORTANT: Do NOT run this unless you explicity want to create a new pixi project
#
# 1. initialize pixi project (in this case the pyproject.toml file had already existed)
pixi init . --format pyproject
# 2. add specified python version
pixi add python=3.11
# 3. add packages (note this will use pixi magic to determine/fix package version ranges)
pixi add $(cat package_names.txt)
# 4. add pypi-packages, if any (note this will use pixi magic to determine/fix package version ranges)
pixi add --pypi $(cat pypi_package_names.txt)
```

---

## QUICK START

```python
from project_kit.config_handler import ConfigHandler
from project_kit.utils import Timer

# Set up configuration (requires .pkit file in project root)
ch = ConfigHandler()

# Access configuration values
database_url = ch.get('database_url', 'sqlite:///default.db')
api_key = ch.api_key  # Raises KeyError if not found

# Use timer utility
timer = Timer()
timer.start()
# ... do some work ...
print(f"Elapsed time: {timer.state()}")
timer.stop()
```

---

## COMPONENTS

### Config Handler

The config_handler module provides the `ConfigHandler` class for unified configuration management across your project. It supports YAML configuration files, environment-specific overrides, and integration with project constants.

**Key Features:**
- Automatic project root detection via `.pkit` file
- YAML-based configuration with environment support
- Constants module integration with protection against overrides
- Multiple access patterns (dict-style, attribute-style, get with defaults)
- Environment variable support for configuration switching

**Setup Requirements:**
1. Create a `.pkit` file in your project root (see [.pkit Configuration](#pkit-configuration))
2. Create a `config/` directory with your YAML configuration files
3. Optionally create a `constants.py` module for project constants

### Job Runner

Tool for cleanly executing sequences of script steps in a controlled manner.

### Config Interface

Decorator that passes configuration arguments from YAML files to Python methods, enabling clean separation of code and configuration.

### Utilities

Collection of utility functions and classes including:
- `Timer`: Simple timing class for measuring elapsed time
- `dir_search`: Search parent directories for specific files
- `read_yaml`: YAML file reading with key path extraction

---

## .pkit Configuration

The `.pkit` file is a YAML configuration file that must be placed in your project's root directory.

**Setup:**
1. Copy `dot_pkit` file to your project root
2. Rename it to `.pkit` (with the leading dot)

This file serves two purposes:

1. it helps pkit locate the root of your project
2. it contains locations, and names of files, and env-keys

In almost all cases you will not need to edit `.pkit`. It is easiest to follow the standard-defaults. Nonetheless, if the naming conventions do create conflicts for your project feel free to change them.

The most likely configuration to edit is "log_folder" - the directory for log files.

**Example .pkit file:**
```yaml
# Path and Directory Configuration
config_folder: "config"              # Directory containing your YAML configuration files
config_filename: "config.yaml"       # Main configuration file name within config_folder
jobs_folder: "jobs"                  # Directory for job runner scripts (if using job runner)
log_folder: "../logs"                # Directory for log files (relative to project root)
constants_module_name: "constants"   # Name of Python module containing project constants

# Environment Configuration
project_kit_env_var_name: "PROJECT_KIT.ENV_NAME"  # Environment variable name for environment-specific configs
default_env_key: "DEFAULT_ENV"                    # Key in main config file that specifies default environment
```

**Environment-Specific Configuration:**
- Set `PROJECT_KIT.ENV_NAME=development` environment variable
- ConfigHandler will load `config/development.yaml` to override base config
- Use `DEFAULT_ENV` key in main config to specify fallback environment

---

## DOCUMENTATION

For detailed API documentation, see the docstrings in each module:
- `project_kit.config_handler.ConfigHandler` - Main configuration class
- `project_kit.utils` - Utility functions and Timer class
- `project_kit.constants` - Project constants

---

## STYLE GUIDE

Following PEP8. See [setup.cfg](./setup.cfg) for exceptions. Keeping honest with `pycodestyle .`
