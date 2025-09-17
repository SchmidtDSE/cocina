# Project Kit


Project Kit (PKIT) is a collection of tools for building out python projects. PKIT contains:

1. [ConfigHandler](#confighandler): used for mangaing constants and configuation for python projects
2. [ConfigArgs](#configargs): used to manage job run configurations: allows the job specific args and kwargs for running a job to be handled through config files.
3. a job cli: a cli that makes it easy to launch and run jobs using yaml files for both project configuration and run configuration.
4. utilities such as timers, loaders and custom loggers

## TODO

- [ ] Logging/Printing
- [ ] Multiple Jobs with 1 call to cli (?)
- [ ] Rewrite README (other md-docs)

## Table of Contents

- [Install/Requirements](#installrequirements)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
  - [Configuration Structure](#configuration-structure)
  - [ConfigHandler](#confighandler)
  - [ConfigArgs](#configargs)
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
from project_kit.config_handler import ConfigHandler, ConfigArgs
from project_kit.utils import Timer

# Set up configuration (requires .pkit file in project root)
ch = ConfigHandler()

# Access configuration values
database_url = ch.get('database_url', 'sqlite:///default.db')
api_key = ch.api_key  # Raises KeyError if not found

# Load job-specific configuration
ca = ConfigArgs('my_job')
job_module = ca.import_job_module()

# Use timer utility
timer = Timer()
timer.start()
# ... do some work ...
print(f"Elapsed time: {timer.state()}")
timer.stop()
```

---

## CONFIGURATION

### Configuration Structure

Project Kit uses a standardized configuration structure that supports both general project settings and job-specific configurations.

**Main Configuration Files (under `project_root/config/`):**

1. **`config.yaml`** - General configuration across all environments
   ```yaml
   database_url: "postgresql://localhost/myapp"
   api_timeout: 30
   log_level: "INFO"
   DEFAULT_ENV: "development"  # Default environment if not specified
   ```

2. **`<env_name>.yaml`** - Environment-specific values (overwrites `config.yaml`)
   ```yaml
   # config/production.yaml
   database_url: "postgresql://prod-server/myapp"
   log_level: "ERROR"
   ```

   ```yaml
   # config/development.yaml
   database_url: "sqlite:///dev.db"
   log_level: "DEBUG"
   ```

**Job Configuration Files (under `project_root/config/args/`):**

Job-specific configuration files contain method arguments and job settings:

```yaml
# config/args/data_processing.yaml
job: "data_processing"  # Points to jobs/data_processing.py

config:
  batch_size: 1000
  parallel_workers: 4

process_data:
  args: ["input.csv"]
  kwargs:
    output_format: "parquet"
    validate: true

validate_results:
  threshold: 0.95
  send_alerts: true
```

### ConfigHandler

The [`ConfigHandler`](./project_kit/config_handler.py#L218) class provides unified configuration management using YAML files, constants, and environment variables.

**Basic Usage:**
```python
from project_kit.config_handler import ConfigHandler

# Initialize with automatic project root detection
ch = ConfigHandler()

# Access configuration values
db_url = ch.get('database_url', 'default_value')  # With fallback
api_key = ch['api_key']                          # Direct access (raises KeyError if missing)
timeout = ch.api_timeout                         # Attribute access

# Check if key exists
if 'optional_setting' in ch:
    value = ch.optional_setting

# Update configuration at runtime
ch.update(new_setting='value')                   # Keyword arguments
ch.update({'batch_size': 500})                   # Dictionary merge
ch.update('config/additional.yaml')              # Load from YAML file
```

**Environment-Specific Loading:**
```bash
# Set environment variable to load config/production.yaml
export PROJECT_KIT.ENV_NAME=production

# Or use development environment
export PROJECT_KIT.ENV_NAME=development
```

**With Constants Module:**
```python
# If you have a constants.py module
ch = ConfigHandler('/path/to/your/module')

# Constants take precedence over config files
# Config files cannot overwrite constants (protection)
```

### ConfigArgs

The [`ConfigArgs`](./project_kit/config_handler.py#L501) class manages job-specific configuration and method arguments, providing structured access to job parameters.

**Basic Usage:**
```python
from project_kit.config_handler import ConfigArgs

# Load job configuration
ca = ConfigArgs('data_processing')  # Loads config/args/data_processing.yaml

# Access method arguments
process_data_method(*ca.process_data.args, **ca.process_data.kwargs)
validate_results(**ca.validate_results.kwargs)

# Import and run the job module
job_module = ca.import_job_module()  # Imports jobs/data_processing.py
job_module.main(*ca.main.args, **ca.main.kwargs)
```

**Advanced Usage:**
```python
# Use with existing ConfigHandler
ch = ConfigHandler()
ca = ConfigArgs('my_job', config_handler=ch)

# Override configuration at runtime
user_overrides = {'batch_size': 2000}
ca = ConfigArgs('my_job', user_config=user_overrides)

# Access all available method configurations
print(f"Available methods: {ca.property_names}")
for method_name in ca.property_names:
    args_kwargs = getattr(ca, method_name)
    print(f"{method_name}: args={args_kwargs.args}, kwargs={args_kwargs.kwargs}")
```

**Job Configuration File Structure:**
```yaml
# config/args/example_job.yaml
job: "data_pipeline"           # Points to jobs/data_pipeline.py

# Global configuration updates
config:
  database_url: "sqlite:///job.db"

# Environment-specific overrides
env:
  production:
    database_url: "postgresql://prod/job"
  development:
    debug_mode: true

# Method configurations
extract_data:
  args: ["source_table"]
  kwargs:
    limit: 10000
    filter_active: true

transform_data:
  batch_size: 500
  parallel: true

load_data:
  args: ["target_table"]
  kwargs:
    if_exists: "replace"
    index: false
```

---

## COMPONENTS

### Config Handler

The [`config_handler`](./project_kit/config_handler.py) module provides the `ConfigHandler` class for unified configuration management across your project. See the [Configuration](#configuration) section for detailed usage examples and configuration structure.

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
- [`project_kit.config_handler.ConfigHandler`](./project_kit/config_handler.py#L218) - Main configuration class
- [`project_kit.config_handler.ConfigArgs`](./project_kit/config_handler.py#L501) - Job-specific configuration management
- [`project_kit.utils`](./project_kit/utils.py) - Utility functions and Timer class
- [`project_kit.constants`](./project_kit/constants.py) - Project constants

---

## STYLE GUIDE

Following PEP8. See [setup.cfg](./setup.cfg) for exceptions. Keeping honest with `pycodestyle .`
