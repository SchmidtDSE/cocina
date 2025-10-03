# Project Kit

Project Kit (PKIT) is a comprehensive collection of tools for building structured Python projects. It provides sophisticated configuration management, job execution capabilities, and professional CLI interfaces.

## Core Components

1. **[ConfigHandler](#confighandler)** - Unified configuration management using YAML files, constants, and environment variables
2. **[ConfigArgs](#configargs)** - Job-specific configuration loading with structured argument access
3. **[CLI](#cli)** - Command-line interface for project initialization and job execution
4. **[Tools](#tools)** - Utilities including [Timer](#timer), [Printer](#printer), and file system helpers


---

## 📋 Table of Contents

**Getting Started:**
- [Install](#install)
- [Initialize](#initialize)
- [Overview](#overview)
  - [Key Concepts](#key-concepts)
  - [Before and After](#before-and-after)
- [Example](#example)
  - [Advanced Features](#advanced-features)

**Configuration:**
- [PKit Configuration](#pkit-configuration)
- [Configuration Files](#configuration-files)
  - [ConfigHandler](#confighandler)
  - [ConfigArgs](#configargs)

**Usage:**
- [CLI](#cli)
  - [Initialize Project](#initialize-project)
  - [Run Jobs](#run-jobs)
- [Tools](#tools)
  - [Printer](#printer)
  - [Timer](#timer)

**Development:**
- [Development](#development)
- [Documentation](#documentation)
- [Contributing](#contributing)

---

## Install

```bash
git clone https://github.com/SchmidtDSE/project_kit.git
```

Add to your `pyproject.toml`:
```toml
[tool.pixi.pypi-dependencies]
project_kit = { path = "path/to/project_kit", editable = true }
```

## Initialize

```bash
pixi run pkit init --log_dir logs --package your_package_name
```

> See [PKit Configuration](#pkit-configuration) for detailed initialization options.


---

## Overview

Project Kit separates **configuration** (values that can change) from **constants** (values that never change) and **job arguments** (run-specific parameters).

### Key Concepts

- **ConfigHandler** (`ch`) - Manages constants and main configuration
  - Constants: `your_module/constants.py` (protected from modification)
  - Config: `config/config.yaml` + environment overrides
  - Usage: `ch.DATABASE_URL`, `ch.MAX_SCALE`

- **ConfigArgs** (`ca`) - Manages job-specific run configurations
  - Job configs: `config/args/job_name.yaml`
  - Usage: `*ca.method_name.args, **ca.method_name.kwargs`

### Before and After

**Traditional approach:**
```python
def main():
    data = load_data("hardcoded_source", limit=1000, debug=True)
    data = process_data(data, scale=100, validate=False)
    save_data(data, "hardcoded_output", format="json")
```

**With Project Kit:**
```python
def run(config_args, printer=None):
    data = load_data(*config_args.load_data.args, **config_args.load_data.kwargs)
    data = process_data(data, *config_args.process_data.args, **config_args.process_data.kwargs)
    save_data(data, *config_args.save_data.args, **config_args.save_data.kwargs)
```

All parameters are now externalized to YAML configuration files, making scripts reusable and maintainable.

---

## Example

**Project Structure:**
```
my_project/
├── config/
│   ├── config.yaml           # Main configuration
│   ├── prod.yaml            # Production overrides
│   └── args/
│       └── data_pipeline.yaml  # Job configuration
└── jobs/
    └── data_pipeline.py     # Job implementation
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
pixi run pkit job data_pipeline

# Production environment
pixi run pkit job data_pipeline --env prod
```

> See the [pkit_example/](pkit_example/) directory for complete working examples.

### Advanced Features

- **Logging with Printer**: Add `printer.message()` calls for professional output and logging
- **Notebook Integration**: Use `ConfigArgs('job_name')` directly in notebooks and scripts
- **Legacy Support**: Jobs without configs can use `main()` method instead of `run()`

> For detailed documentation on all features, see the [complete documentation](../project_kit.wiki/).

---

## PKit Configuration

The `.pkit` file contains project settings and must be in your project root. It defines:
- Configuration file locations and naming conventions
- Project root directory location
- Environment variable names

**Required:** Every project must have a `.pkit` file at the root.

**Options:**
- `--log_dir`: Enable automatic log file creation
- `--package`: Specify main package for constants loading
- `--force`: Overwrite existing `.pkit` file

---

## Configuration Files

Project Kit uses YAML files in the `config/` directory:

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
from project_kit.config_handler import ConfigHandler

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
from project_kit.config_handler import ConfigArgs

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
pixi run pkit init --log_dir logs --package your_package
```

### Run Jobs

```bash
# Run a single job
pixi run pkit job data_pipeline

# Run with specific environment
pixi run pkit job data_pipeline --env prod

# Run multiple jobs
pixi run pkit job job1 job2 job3

# Dry run (validate without executing)
pixi run pkit job data_pipeline --dry_run
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
from project_kit.printer import Printer

printer = Printer(header='MyApp')
printer.start('Processing begins')
printer.message('Status update', count=42, status='ok')
printer.stop('Complete')
```

### Timer
Simple timing functionality with duration tracking.

```python
from project_kit.utils import Timer

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

**[📖 Complete Documentation](../project_kit.wiki/)** | **[🚀 Getting Started](../project_kit.wiki/getting-started.md)** | **[⚙️ Configuration](../project_kit.wiki/configuration.md)** | **[🔧 API Reference](../project_kit.wiki/api.md)**

### Quick Links

- **[Getting Started](../project_kit.wiki/getting-started.md)** - Installation, initialization, and first job
- **[Configuration Guide](../project_kit.wiki/configuration.md)** - Complete configuration management
- **[Job System](../project_kit.wiki/jobs.md)** - Creating and running jobs
- **[CLI Reference](../project_kit.wiki/cli.md)** - Command-line interface
- **[Examples](../project_kit.wiki/examples.md)** - Detailed usage examples
- **[Advanced Topics](../project_kit.wiki/advanced.md)** - Complex patterns and extensions

## Contributing

See [pkit_example/](pkit_example/) for working examples and [CLAUDE.md](claude/CLAUDE.md) for development guidelines.

## License

CC-BY-4.0