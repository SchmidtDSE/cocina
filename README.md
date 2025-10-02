# Project Kit

Project Kit (PKIT) is a collection of tools for building out python projects. Its main functionality is to manage constants, configuration and arguments, and to simplify/clean-up writing scripts (jobs). These tasks are managed by:

1. [ConfigHandler](#confighandler): a `class` used for managing constants and configuration
2. [ConfigArgs](#configargs): a `class` used to manage arguments/job-run-configurations
3. [CLI](#cli): a cli for launching and running jobs using these configuration files

PKit also includes a serveral other useful [tools](#tools) such a [Timer](#timer), a [Printer (Logger)](#printer), as well as a number of python helpers to read and write files, join strings, search directories etc

**Table of Contents**

- [Setup](#setup)
  - [Install](#install)
  - [Initialize](#initialize)
- [Overview](#overview)
  - [Configuration, Arguments, and Constants](#configuration-arguments-and-constants)
  - [Example](#example)
- [PKit Configuration](#pkit-configuration)
- [Project Config Files](#project-config-files)
  - [ConfigHandler](#confighandler)
  - [ConfigArgs](#configargs)
- [Tools](#tools)
  - [Printer](#printer)
  - [Timer](#timer)
- [Requirements](#requirements)
- [Style Guide](#style-guide)

---

## Setup

### Install

Project will be added to pypi soon. For now install from github:

```bash
git clone https://github.com/SchmidtDSE/project_kit.git
```

Then in your pyproject.toml add

```toml
[tool.pixi.pypi-dependencies]
project_kit = { path = "your/path/to/project_kit", editable = true }
```

### Initialize

PKit must be initialized. This can be managed through the CLI.

```bash
pixi run pkit init (--log_dir <relative-path-to-log-dir>) \
                   (--package <main-package-name>) \
                   (--force) \
```

(see details [below](#pkit-configuration))



---

## Overview


### Configuration, Arguments, and Constants

Before we begin we need to make some definitions and distinctions between, Configuration, Arguments, and Constants. PKit has two main classes to manage these: [ConfigHandler](#confighandler) and [ConfigArgs](#configargs).

#### ConfigHandler: manages the constants and (main-)configuration

An instance `ch` of `ConfigHandler` manages:

- constants: defined in `your_module/constants.py`
  - values that will never change (ie `M2_PER_HECTARE =  10000`)
  - If you attempt to assign a value to one of your constants in a config or arg file an error will be thrown
- config: defined in `config/config.yaml`, or the environment-specific `config/env-name.yaml`
  - values that can change
  - examples include:
    - default values: `def some_method(..., return_array: ch.RETURN_ARRAY):`
    - project config: `uri = f'gs://{ch.GCS_BUCKET}/{ch.GCS_FOLDER}/users.yaml'`

#### ConfigArgs: manages the run configuration for specific jobs/scripts

An instance `ca` of `ConfigArgs` can manage run-configs for a script. Imagine a script with the following:

```python
...

def main():
  data = load_data(...)
  data = process_data(data, ...)
  save_data(data, ...)

if __name__ == "__main__":
    main()
```

There could be a lot of configuration hidden in the `...`s.  There is probably some cli-arg-parsing, hard-coded constants, and when calling `load_data`, `process_data` and `save_data` whatever parameters that are needed for this particular run. Moreover, these hard-coded constants and parameter values might be changing that configuration on a regular basis. 

With PKit we can have a single job

```python
...

def run(config_args, printer=None) -> None:
  data = load_data(*config_args.load_data.args, **config_args.load_data.kwargs)
  data = process_data(data, *config_args.process_data.args, **config_args.process_data.kwargs)
  save_data(data, *config_args.save_data.args, **config_args.save_data.kwargs)
```

In our partial script above this almost looks more complicated. But its **much** simpler.
The cli-arg-parsing is handled by pkit's [CLI](#cli), and the parameter values and hard-coded constants are handled by `ca` (and sometimes `ch`).
Remember any method can take `*args, **kwargs` even if the method has no args/kwargs (ask long as `args = []`, `kwargs = {}`). 

When distinguishing when to use the main/env-configuration files, or a job-config file, ask yourself: is this a run parameter? do i want to access it directly (such as `ch.MAX_SCALE`) or through args/kwargs `(..., *config_args.method_name.args, **config_args.method_name.kwargs)`.

---

### Example

Let's quickly walk through an example. Assume we have the following in our config directory:

```bash
├── config
│ ├── args               # This directory contains argument (args and kwargs) for specific scripts
│ │ ├── job_1.yaml
│ │ ├── job_2.yaml
│ │ └── job_group_1
│ │     └── job_a1.yaml
│ ├── config.yaml     # This file contains constants/configurations to be used throughout ones package
│ ├── dev.yaml        # Updates the values (or adds new values to) config.yaml for a "dev" env
│ ├── prod.yaml       # Updates the values (or adds new values to) config.yaml for a "prod" env
│ └── silly_env.yaml  # ... (you can name your envs anything you like dev/prod were just examples)
```

And some "job" modules:

```bash
├── jobs
│ ├── job_1.py
│ ├── job_2.py
│ └── job_group_1
│     └── job_a1.py
```

Where `config/args/job_group_1/job_a1.yaml` looks like

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
and `jobs/job_group_1/job_a1.py` looks like

```python
from project_kit.config_handler import ConfigHandler
ch = ConfigHandler()

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

We can now run this job (`jobs.job_group_1.job_a1.run(...)`) using the [CLI](#cli):

```bash
# run jobs.job_group_1.job_a1 for the default env
pixi run pkit job job_group_1.job_a1

# run jobs.job_group_1.job_a1 for the "prod" env
pixi run pkit job job_group_1.job_a1 --env prod
```

#### PRINTER

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

#### USER CODEBASE/NOTEBOOKS

Although the main focus is on building and running configured "jobs"/scripts, [ConfigArgs](#configargs) can also be used in your code (a notebook for example):

```python
# Load job-specific configuration
ca = ConfigArgs('job_group_1.job_a1')
jobs.job_group_1.job_a1.step_1(*ca.step_1.args, **ca.step_1.kwargs)
```

#### UNCONFIGURED JOBS

It may be, for instance to support existing scripts, you may want to run a script that does not have a configuration file. in this case, rather than having method `run(...)` in your job module/script, have a method `main()` that takes no arguments.

When running a job, the priority order is:

1. `run(config_args, printer)`
2. `run(config_args)`
3. `main()`

---

## PKit Configuration

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

### NOTES

- If `log_dir` is provided `Printer` will automatically write logs (as well as print to screen)
- If `package` is provided ConfigHandler will always look for `package.constants` when loading. If your project has only 1 package, this is probably the best way to manage it. However, the code-base also allows you to pass it directly and attempts to auto-detect if from the file-path.
- If `--force` flag is added it will overwrite existing `.pkit files` otherwise it would throw an error
- If you prefer you can always just copy `dot_pkit` into your directory and rename it to `.pkit`

---

## Project Config Files

Project Kit provides a flexible configuration system that supports both general project settings and job-specific configurations. The system uses YAML files and supports environment-specific overrides. By default, the config files all live in `config/`. Here's an example:

```bash
├── config
│ ├── args              # This directory contains argument (args and kwargs) for specific scripts
│ │ ├── job_1.yaml      # This contains the run configuration for job_1
│ │ ├── ...
│ │ └── group_1         # Run configurations can be grouped into subfolders
│ │     ├── g1_a.yaml
│ │     └── g1_b.yaml
│ ├── config.yaml       # This file contains constants/configurations to be used throughout ones package
│ ├── dev.yaml          # Updates the values (or adds new values to) config.yaml for a "dev" env
│ └── silly_env.yaml    # ... (you can name your envs anything you like dev/prod were just examples)
```

**Main Configuration Files (under `project_root/config/`):**

- **`config.yaml`** - General configuration across all environments
- **`<env_name>.yaml`** - Environment-specific values (overwrites `config.yaml`)

**Job Configuration Files (under `project_root/config/args/`):**

- Job-specific configuration files contain method arguments and job settings

### ConfigHandler

The [`ConfigHandler`](./project_kit/config_handler.py) class provides unified configuration management using YAML files, constants, and environment variables.

(more docs to come: see Quick Start for examples)

TODO: more detailed explanation
TODO: explain the role of `constants.py`

### ConfigArgs

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
  debug_mode: false

# environment-specific overrides
env:
  prod:
    load_data: true
  dev:
    load_data: false
    debug_mode: true

# -----------------------------------------------------------------------------
# The rest of the keys lead to properties on `ca = ConfigArgs()` instances
# -----------------------------------------------------------------------------
extract_data:
  args: ["source_table"]
  kwargs:
    limit: 10000
    filter_active: true
    debug: "debug_mode"

compute_for_scales:
  - 10
  - 100
  - MAX_SCALE

transform_data:
  url: database_url
  batch_size: 500
  parallel: true

load_data: load_data
```

This data can now be accessed through a `ca = ConfigArgs()` instance. For example, in the "prod" environment: `ca.extract_data.args` returns `["source_table"]`, and  `ca.extract_data.kwargs` returns 

```python
{
    "limit": 10000
    "filter_active": True
    "debug": False
}
```

Note: in the "dev" environment we would have recieved `debug: True`. 

#### PARSING RULES

ConfigArgs parses the values using the following parsing-rules:

- If value is a dict:
  - If keys are exclusively 'args' and/or 'kwargs': extract `args`/`kwargs` from value
  - Otherwise: `args = []` and `kwargs = value`
- If value is a list or tuple: `args = value`, `kwargs = {}`
- Otherwise: `args = [value]`, `kwargs = {}`

So for the above job-config (in "dev" environment"), assuming `MAX_SCALE = 1000` is defined in a main-configuration file:

```python
ca.compute_for_scales.args # ==> [10, 100, 1000] 
ca.compute_for_scales.kwargs # ==> {}

ca.transform_data.args # ==> [] 
ca.transform_data.kwargs # ==> {'url': 'sqlite:///job.db', 'batch_size': 500, 'parallel': True}

ca.load_data.args # ==> [True]
ca.load_data.kwargs # ==> {}
```

#### SELF REFERENTIAL MAGIC

Note that something else is happening in the above description. `ca.transform_data.kwargs` is returning the `database_url` defined in the `config:` section, `ca.extract_data.kwargs` is returning `debug` mode from either the `env.prod:` or `env.dev:` section, and `ca.load_data.args` is returning `MAX_SCALE` from the main-configuration (or environment-configuration) files discussed [above](#confighandler). 

---

## Tools

### Printer

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

### Timer

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

## Style Guide

Following PEP8. See [setup.cfg](./setup.cfg) for exceptions. Keeping honest with `pycodestyle .`