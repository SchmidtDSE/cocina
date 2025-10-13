# Cocina
 
Cocina is a collection of tools for building structured Python projects. It provides sophisticated configuration management, job execution capabilities, and a professional CLI interface.

## Core Components

1. **[ConfigHandler](#confighandler)** - Unified configuration management, constants, and environment variables
2. **[ConfigArgs](#configargs)** - Job-specific configuration loading with structured argument access
3. **[CLI](#cli)** - Command-line interface for project initialization and job execution

---

## Table of Contents

- [Getting Started](#getting-started)
    - [Overview](#overview)
    - [Example](#example)
    - [Advanced Features](#advanced-features)
- [cocina Configuration](#cocina-configuration)
- [Configuration Files](#configuration-files)
  - [ConfigHandler](#confighandler)
  - [ConfigArgs](#configargs)
- [CLI](#cli)
  - [Initialize Project](#initialize-project)
  - [Run Jobs](#run-jobs)
- [Tools](#tools)
  - [Printer](#printer)
  - [Timer](#timer)
- [Development](#development)
- [Documentation](#documentation)


---

## Getting Started

**INSTALL**:

```bash
git clone https://github.com/SchmidtDSE/cocina.git
```

Add to your `pyproject.toml`:
```toml
[tool.pixi.pypi-dependencies]
cocina = { path = "path/to/cocina", editable = true }
```

**INITIALIZE**:

```bash
pixi run cocina init --log_dir logs --package your_package_name
```

> See [cocina Configuration](#cocina-configuration) for detailed initialization options.


---

### Overview

Cocina separates **configuration** (values that can change) from **constants** (values that never change) and **job arguments** (run-specific parameters).

#### Key Concepts

- **ConfigHandler** (`ch`) - Manages constants and project configuration
  - Constants: `your_module/constants.py` (protected from modification)
  - General Config: `config/config.yaml`
  - Env Config: `config/<environment-name>.yaml`
  - Usage: `ch.DATABASE_URL`, `ch.get(MAX_SCALE, 1000)`

- **ConfigArgs** (`ca`) - Manages job-specific run configurations
  - Job configs: `config/args/job_name.yaml`
  - Usage: To run method `method_name`: `method_name(*ca.method_name.args, **ca.method_name.kwargs)`

**Note**: names of configuration and job directories and files can be customized in [.cocina](#cocina-configuration).

#### Before and After

**Traditional approach:**
```python
SOURCE = "path/to/src.parquet"
OUTPUT_DEST = "path/to/output"

def main():
    data = load_data(SOURCE, limit=1000, debug=True)
    data = process_data(data, scale=100, validate=False)
    save_data(data, OUTPUT_DEST, format="json")

if __name__ == "__main__":
    main()
```

**With Cocina:**
```python
def run(config_args):
    data = load_data(*config_args.load_data.args, **config_args.load_data.kwargs)
    data = process_data(data, *config_args.process_data.args, **config_args.process_data.kwargs)
    save_data(data, *config_args.save_data.args, **config_args.save_data.kwargs)
```

All parameters are now externalized to YAML configuration files, making scripts reusable and maintainable. CLI mangagement/arg-parsing is handled through the cocina [CLI](#cli)

### Example

**Project Structure:**
```
my_project/
├── my_package/                 # Python package
│   ├── constants.py            # Project Constants (protected from modification)
│   ├── ...                     # Modules
│   └── data_manager.py         # Named example python module
├── config/
│   ├── config.yaml             # Main configuration
│   ├── prod.yaml               # Production configuration overrides
│   └── args/
│       └── data_pipeline.yaml  # Job configuration
└── jobs/
    └── data_pipeline.py        # Job implementation
```

**Configuration (`config/args/data_pipeline.yaml`):**
```yaml
extract_data:
  args: ["source_table"]
  kwargs:
    limit: 1000
    debug: false

transform_data:
  scale: 100
  validate: true

save_data:
  - "output_table"
```

**Job Implementation (`jobs/data_pipeline.py`):**
```python
def run(config_args, printer=None):
    data = extract_data(*config_args.extract_data.args, **config_args.extract_data.kwargs)
    data = transform_data(data, *config_args.transform_data.args, **config_args.transform_data.kwargs)
    save_data(*config_args.save_data.args, **config_args.save_data.kwargs)
```

**Running Jobs:**
```bash
# Default environment
pixi run cocina job data_pipeline

# Production environment
pixi run cocina job data_pipeline --env prod
```

#### RUN AND MAIN METHODS

When running a job, the CLI requires either a `run` method that takes arguments `config_args: ConfigArgs`, `printer: Printer`, or a `run` method that takes only `config_args: ConfigArgs`, or a `main` method that does not have any arguments.

Priority ordering is:

1. `run(config_args, printer)`   | passing both a `ConfigArgs` and `Printer` instance
2. `run(config_args)`            | passing a `ConfigArgs` instance
3. `main()`                      | for jobs without configuration (legacy scripts)


#### USER CODEBASE/NOTEBOOKS

Although the main focus is on building and running configured "jobs", [ConfigArgs](#configargs) can also be used in your code (a notebook for example):

```python
# Load job-specific configuration
ca = ConfigArgs('job_group_1.job_a1')
jobs.job_group_1.job_a1.step_1(*ca.step_1.args, **ca.step_1.kwargs)
```

---

## cocina Configuration

The `.cocina` file contains project settings and must be in your project root. It defines:
- Configuration file locations and naming conventions
- Project root directory location
- Environment variable names

**Required:** Every project must have a `.cocina` file at the root.

**Options:**
- `--log_dir`: Enable automatic log file creation
- `--package`: Specify main package for constants loading
- `--force`: Overwrite existing `.cocina` file

---

## Configuration Files

Cocina uses YAML files in the `config/` directory:

```
config/
├── config.yaml           # Main configuration
├── dev.yaml             # Development environment overrides
├── prod.yaml            # Production environment overrides
└── args/                # Job-specific configurations
    ├── job_name.yaml    # Individual job config
    └── group_name/      # Grouped job configs
        └── job_a.yaml
```

**Configuration Types:**
- **Main Config**: `config.yaml` - shared across all environments
- **Environment Config**: `{env}.yaml` - environment-specific overrides
- **Job Config**: `args/{job}.yaml` - job-specific parameters and arguments

### ConfigHandler

Manages constants and main configuration with environment support.

```python
from cocina.config_handler import ConfigHandler

ch = ConfigHandler()
print(ch.DATABASE_URL)  # From config.yaml
print(ch.MAX_SCALE)     # From constants.py (protected)
```

**Features:**
- Loads constants from `your_package/constants.py`
- Loads configuration from `config/config.yaml`
- Environment-specific overrides from `config/{env}.yaml`
- Dict-style and attribute access patterns

### ConfigArgs

Loads job-specific configurations with structured argument access.

```python
from cocina.config_handler import ConfigArgs

ca = ConfigArgs('data_pipeline')
# Access method arguments
ca.extract_data.args     # ["source_table"]
ca.extract_data.kwargs   # {"limit": 1000, "debug": False}
```

**YAML Configuration Parsing:**
- Dict with `args`/`kwargs` keys → extracts args and kwargs
- Dict without special keys → `args=[]`, `kwargs=dict`
- List/tuple → `args=value`, `kwargs={}`
- Single value → `args=[value]`, `kwargs={}`

**Features:**
- Environment-specific overrides
- Reference resolution from main config
- Dynamic value substitution 

---

## CLI

### Initialize Project

```bash
pixi run cocina init --log_dir logs --package your_package
```

### Run Jobs

```bash
# Run a single job
pixi run cocina job data_pipeline

# Run with specific environment
pixi run cocina job data_pipeline --env prod

# Run multiple jobs
pixi run cocina job job1 job2 job3

# Dry run (validate without executing)
pixi run cocina job data_pipeline --dry_run
```

**Options:**
- `--env`: Environment configuration to use (dev, prod, etc.)
- `--verbose`: Enable detailed output
- `--dry_run`: Validate configuration without running


---

## Tools

### Printer
Professional output with timestamps, headers, and optional file logging.

```python
from cocina.printer import Printer

printer = Printer(header='MyApp')
printer.start('Processing begins')
printer.message('Status update', count=42, status='ok')
printer.stop('Complete')
```

### Timer
Simple timing functionality with duration tracking.

```python
from cocina.utils import Timer

timer = Timer()
timer.start()           # Start timing
print(timer.state())    # Current elapsed time
print(timer.now())      # Current timestamp
stop_time = timer.stop()     # Stop timing
print(timer.delta())    # Total duration string
```

> See [complete documentation](docs/) for all utility functions and helpers.

---

## Development

**Requirements:** Managed with [Pixi](https://pixi.sh/latest) - no manual environment setup needed.

```bash
# All commands use pixi
pixi run jupyter lab
```

**Style:** Follows PEP8 standards. See [setup.cfg](./setup.cfg) for project-specific rules.

---

## Documentation

- **[Getting Started](/wiki/getting-started)** - Installation, initialization, and first job
- **[Configuration Guide](/wiki/configuration)** - Complete configuration management
- **[Job System](/wiki/jobs)** - Creating and running jobs
- **[CLI Reference](/wiki/cli)** - Command-line interface
- **[Examples](/wiki/examples)** - Detailed usage examples
- **[Advanced Topics](/wiki/advanced)** - Complex patterns and extensions
