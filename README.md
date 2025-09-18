# Project Kit

Project Kit (PKIT) is a collection of tools for building out python projects. Its main functionality is to manage constants, configuration and arguments, and to simplify/clean-up writing scripts (jobs). These tasks are managed by:

1. [ConfigHandler](#confighandler): a `class` used for managing constants and configuration
2. [ConfigArgs](#configargs): a `class` used to manage arguments/job-run-configurations
3. [CLI](#cli): a cli for launching and running jobs using these configuration files

(TODO: CONFIG VS CONSTANTS VS ARGUMENTS)

PKit also includes a serveral other useful [tools](#tools) such a [Timer](#timer), a [Printer (Logger)](#printer), as well as a number of python helpers to read and write files, join strings, search directories etc

## Table of Contents

- [Setup](#setup)
- [Quick Start](#quick-start)
- [PKit Configuration](#pkit-configuration)
- [Configuration](#configuration)
  - [Configuration Structure](#configuration-structure)
  - [ConfigHandler](#confighandler)
  - [ConfigArgs](#configargs)
- [Tools](#tools)
  - [Printer](#printer)
  - [Timer](#timer)
- [Style Guide](#style-guide)

---

# Setup

## Install

Project will be added to pypi soon. for now here are the install steps:

```bash
git clone https://github.com/SchmidtDSE/project_kit.git
```

Then in your pyproject.toml add

```toml
[tool.pixi.pypi-dependencies]
project_kit = { path = "your/path/to/project_kit", editable = true }
```

## Initialize

PKit must be initialized. This can be managed through the CLI.

```bash
pixi run pkit init (--log_dir <relative-path-to-log-dir>) \
                   (--package <main-package-name>) \
                   (--force) \
```

(see details [below](#pkit-configuration))


## Requirements

Requirements are managed through a [Pixi](https://pixi.sh/latest) "project" (similar to a conda environment). After pixi is installed use `pixi run <cmd>` to ensure the correct project is being used. For example,

```bash
# launch jupyter
pixi run jupyter lab .

# run a script
pixi run python scripts/hello_world.py
```

The first time `pixi run` is executed the project will be installed (note this means the first run will be a bit slower). Any changes to the project will be updated on the subsequent `pixi run`. It is unnecessary, but you can run `pixi install` after changes - this will update your local environment, so that it does not need to be updated on the next `pixi run`.

Note, the repo's `pyproject.toml`, and `pixi.lock` files ensure `pixi run` will just work. No need to recreate an environment. Additionally, the `pyproject.toml` file includes `project_kit = { path = ".", editable = true }`. This line is equivalent to `pip install -e .`, so there is no need to pip install this module.

The project was initially created using a `package_names.txt` and the following steps. Note that this should **NOT** be re-run as it will create a new project (potentially changing package versions).

```bash
#
# IMPORTANT: Do NOT run this unless you explicitly want to create a new pixi project
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

# Quick Start

As a quick-start we'll just quickly walk through an example. Assume we have the following in our config directory:

```bash
├── config
│ ├── args               # This directory contains argument (args and kwargs) for specific scripts
│ │ ├── job_1.yaml
│ │ ├── job_2.yaml
│ │ └── job_group_1
│ │     └── job_a1.yaml
│ ├── config.yaml         # This file contains constants/configurations to be used throughout ones package
│ ├── dev.yaml        # Updates the values (or adds new values to) config.yaml for a "dev" env
│ ├── prod.yaml       # Updates the values (or adds new values to) config.yaml for a "prod" env
│ └── some_silly_env.yaml # ... (you can name your envs anything you like dev/prod were just examples)
```

```python
from project_kit.config_handler import ConfigHandler

# Here `ConfigHandler()` loads the configuration in config.yaml, and then (if an env has been set) updates it with the correct env-conf (ie prod.yaml). Note, it may also include constants defined in a `package_name.constants` module (more details below).

ch = ConfigHandler()
database_url = ch.get('database_url', 'sqlite:///default.db')
api_key = ch.api_key  # Raises KeyError if not found

def some_function(value: str = ch.CONFIGURED_VALUE):
  pass
```

And some "job" modules:

```bash
├── jobs
│ ├── job_1.py
│ ├── job_2.py
│ └── job_group_1
│     └── job_a1.py
```

Here `config/args/job_group_1/job_a1.yaml` looks like

```yaml
# config/args/job_group_1/job_a1.yaml
step_1:
  args:
    - value1
    - value2
  kwargs:
    kwarg1: key_value1
    kwarg2: key_value2

step_2:
  kwarg1: key_value1
  kwarg2: key_value2
  kwarg3: key_value3

step_3:
  - value1
  - value2
  - value3
```

```python
# jobs.job_group_1.job_a1

...

def step_1(arg1, arg2, kwarg1=None, kwarg2=None):
  return dict(...)

def step_2(result_1, kwarg1=None, kwarg2=None, kwarg3=None):
  pass

def step_3(arg1, arg2, arg3):
  pass

def run(config_args):
  result_1 = step_1(*config_args.step_1.args, **config_args.step_1.kwargs)
  step_2(result_1, *config_args.step_2.args, **config_args.step_2.kwargs)
  step_3(*config_args.step_3.args, **config_args.step_3.kwargs)
```

Now you can use the [ConfigArgs](#configargs) class to run these methods.

```python
# Load job-specific configuration
ca = ConfigArgs('job_group_1.job_a1')
jobs.job_group_1.job_a1.step_1(*ca.step_1.args, **ca.step_1.kwargs)
```

But the `run` method is special: It's what makes it a job! The commands below use the [CLI](#cli) to run `jobs.job_group_1.job_a1.run(...)`

```bash
# run jobs.job_group_1.job_a1 for the default env
pixi run pkit job job_group_1.job_a1

# run jobs.job_group_1.job_a1 for the "prod" env
pixi run pkit job job_group_1.job_a1 --env prod
```

The run method also can take a [`Printer`](#printer) to make it easy to print formatted strings with timestamps, and (if `log_dir` configured in [.pkit](#pkit-configuration)) log them. The following changes to the `run` method will give a nice set of logs

```python

...

def run(config_args, printer=None):
  if printer is None:
    printer = Printer()
    printer.start()
  printer.message('step_1')
  result_1 = step_1(*config_args.step_1.args, **config_args.step_1.kwargs)
  printer.message('step_1.results', **result_1)
  printer.message('step_2')
  step_2(result_1, *config_args.step_2.args, **config_args.step_2.kwargs)
  printer.message('step_3')
  step_3(*config_args.step_3.args, **config_args.step_3.kwargs)
```

---

# PKit Configuration

The [.pkit](dot_pkit) Configuration file contains project_kit settings and conventions. PKit use this file to:

1. set conventions: determine the location and names of key (job and config) files and
   environmental variables
2. determine the project-root.

IMPORTANT: All project-kit projects must include a copy of this file (renamed to .pkit)
           located at the project root.

Generate this file by running:

```bash
pixi run pkit init (--log_dir <relative-path-to-log-dir>) \
                   (--package <main-package-name>) \
                   (--force) \
```

## NOTES

- If `log_dir` is provided `Printer` will automatically write logs (as well as print to screen)
- If `package` is provided ConfigHandler will always look for `package.constants` when loading. If your project has only 1 package, this is probably the best way to manage it. However, the code-base also allows you to pass it directly and attempts to auto-detect if from the file-path.
- If `--force` flag is added it will overwrite existing `.pkit files` otherwise it would throw an error
- If you prefer you can always just copy `dot_pkit` into your directory and rename it to `.pkit`

---

# Configuration

Project Kit provides a flexible configuration system that supports both general project settings and job-specific configurations. The system uses YAML files and supports environment-specific overrides.

## Configuration Structure

**Main Configuration Files (under `project_root/config/`):**

- **`config.yaml`** - General configuration across all environments
- **`<env_name>.yaml`** - Environment-specific values (overwrites `config.yaml`)

**Job Configuration Files (under `project_root/config/args/`):**

- Job-specific configuration files contain method arguments and job settings

## ConfigHandler

The [`ConfigHandler`](./project_kit/config_handler.py) class provides unified configuration management using YAML files, constants, and environment variables.

(more docs to come: see Quick Start for examples)

TODO: more detailed explanation
TODO: explain the role of `constants.py`

## ConfigArgs

The [`ConfigArgs`](./project_kit/config_handler.py) class manages job-specific configuration and method arguments, providing structured access to job parameters.

**Job Configuration File Structure:**

Consider a file `config/args/example_job.yaml`:

```yaml
# -----------------------------------------------------------------------------
# By default config/args/example_job.yaml is connected to jobs/example_job.py
# However, by uncommenting the line below it will be connected with jobs/data_pipeline.py
# -----------------------------------------------------------------------------
# job: "data_pipeline"

# -----------------------------------------------------------------------------
# You can update the configurations managed by ConfigHandler using `config` and `env` keys.
# -----------------------------------------------------------------------------
# global configuration updates
config:
  database_url: "sqlite:///job.db"

# environment-specific overrides
env:
  prod:
    database_url: "postgresql://prod/job"
  dev:
    debug_mode: true

# -----------------------------------------------------------------------------
# The rest of the keys lead to properties on `ca = ConfigArgs()` instances:
#
# For instance extract_data yaml =>
#   - ca.extract_data.args (list) and
#   - ca.extract_data.kwargs (dict)
#
# Parsing rules:
#   - If value is dict:
#     - If keys are exclusively 'args' or 'kwargs': extract args/kwargs from value
#     - Otherwise: args = [] and kwargs = value
#   - If value is list/tuple: args = value, kwargs = {}
#   - Otherwise: args = [value], kwargs = {}
# -----------------------------------------------------------------------------
extract_data:
  args: ["source_table"]
  kwargs:
    limit: 10000
    filter_active: true

compute_for_scales:
  - 10
  - 100
  - 1000

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

# Tools

## Printer

The [`Printer`](./project_kit/printer.py) class provides structured output and logging with timestamps, dividers, and optional file output.

**Basic Usage:**
```python
from project_kit.printer import Printer

# Create printer with header and optional log directory
printer = Printer(header='MyApp', log_dir='/logs')

# Start session (begins timing and creates log file if log_dir specified)
printer.start('Processing begins')

# Print messages with optional dividers and spacing
printer.message('Status update')
printer.message('Error', 'processing', div='*', vspace=2)
printer.message('Info', count=42, status='ok')

# Stop session (prints duration and returns stop time)
stop_time = printer.stop('Processing complete')
```

## Timer

The [`Timer`](./project_kit/utils.py) class provides simple timing functionality with lap support and multiple output formats.

**Basic Usage:**
```python
from project_kit.utils import Timer

# Create and start timer
timer = Timer()
timer.start()

# Check elapsed time
print(f"Elapsed: {timer.state()}")

# Add lap times
timer.lap('checkpoint1')
timer.lap('checkpoint2')

# Stop and get duration
duration = timer.stop()
print(f"Total duration: {timer.delta()}")
```

---

# Style Guide

Following PEP8. See [setup.cfg](./setup.cfg) for exceptions. Keeping honest with `pycodestyle .`