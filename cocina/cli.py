""" cli

License:
    BSD, see LICENSE.md
"""
import os, sys
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
from pprint import pprint
import click
from cocina.constants import cocina_NOT_FOUND, cocina_env_key, cocina_CLI_DEFAULT_HEADER
from cocina.utils import safe_copy_yaml, safe_join
from cocina.config_handler import ConfigArgs, cocinaConfig
from cocina.printer import Printer


#
# CONSTANTS
#
_MISSING_RUN_PART: str = "attribute 'run'"
_MISSING_MAIN_PART: str = "attribute 'main'"


# -------------------------------------------------------------------
# CLI INTERFACE
# -------------------------------------------------------------------
@click.group
@click.pass_context
def cli(ctx):
    ctx.obj = {}


#
# INIT
#
@cli.command(name='init', help='initialize project with .cocina file')
@click.option('--log_dir', '-l',
    type=str,
    required=False,
    help='Log Directory')
@click.option('--package', '-p',
    type=str,
    required=False,
    help='Main Package Name')
@click.option('--force', '-f',
    type=bool,
    required=False,
    is_flag=True)
@click.pass_context
def init(
        ctx,
        log_dir: Optional[str] = cocina_NOT_FOUND,
        package: Optional[str] = cocina_NOT_FOUND,
        force: bool = False):
    src_cocina_path = Path(__file__).parent.parent / 'dot_cocina'
    dest_cocina_path = f'{Path.cwd()}/.cocina'
    safe_copy_yaml(
        src_cocina_path,
        dest_cocina_path,
        log_dir=log_dir,
        constants_package_name=package,
        force=force)
    print(f'cocina: project initialized ({dest_cocina_path})')
    cocina = cocinaConfig.init_for_project()
    pprint(cocina)


#
# JOBS
#
@cli.command(name='job', help='job help text')
@click.argument('jobs', type=str, nargs=-1)
@click.option('--env', '-e', type=str, required=False, help='Environment to run job in')
@click.option('--verbose', '-v',
    type=bool,
    required=False,
    is_flag=True,
    help='Enable verbose output')
@click.option('--dry_run',
    type=bool,
    required=False,
    is_flag=True)
@click.pass_context
def job(
        ctx,
        jobs: str,
        env: Optional[str] = None,
        verbose: bool = True,
        dry_run: bool = False):
    # 1. processs args
    jobs, user_config = _process_jobs_and_user_config(jobs, dry_run)

    # 2. cocina-setup
    cocina, printer = _cocina_printer(*jobs)
    printer.start(vspace=False)

    # 3. set environment (if provided)
    if env:
        printer.message(f"Setting environment: {env}")
        os.environ[cocina_env_key] = env

    # 4. run jobs
    for job in jobs:
        execute_job(job, user_config=user_config, printer=printer)

    # 5. complete
    printer.stop(f"Jobs ({safe_join(jobs)}) completed successfully!")


#
# HELPERS
#
def execute_job(job: str, user_config: Optional[dict] = None, printer: Optional[Printer] = None) -> None:
    if printer is None:
        cocina, printer = _cocina_printer(job)
        printer.start()
    error = False
    printer.set_header(job)
    try:
        config_args = ConfigArgs(job, user_config=user_config)
        printer.vspace()
        job_module = config_args.import_job_module()
        try:
            job_module.run(config_args, printer=printer)
        except TypeError:
            job_module.run(config_args)
        except AttributeError as e:
            if _MISSING_RUN_PART in str(e):
                job_module.main()
            else:
                raise e
    except FileNotFoundError as e:
        printer.stop(f"Job configuration not found", error=e)
        sys.exit(1)
    except ImportError as e:
        printer.stop(f"Failed to import job module", error=e)
        sys.exit(1)
    except AttributeError as e:
        if _MISSING_MAIN_PART in str(e):
            printer.stop(f"Job module missing 'run' xor 'main' function", error=e)
            sys.exit(1)
        else:
            printer.stop(f"Likely missing configuration-value", error=e)
            printer.vspace()
            error = e
    if error:
        raise error


#
# INTERNAL
#
def _cocina_printer(
        *name_parts: str,
        cocina: Optional[cocinaConfig] = None,
        header: str = cocina_CLI_DEFAULT_HEADER) -> Tuple[cocinaConfig, Printer]:
    """Initialize cocinaConfig and Printer instances for CLI operations.

    Args:
        *name_parts: Variable length string arguments to construct log name
        cocina: Existing cocinaConfig instance (creates new if None)
        header: Header string for printer output

    Returns:
        Tuple containing cocinaConfig and Printer instances

    Usage:
        >>> cocina, printer = _cocina_printer('job1', 'task1')
        >>> cocina, printer = _cocina_printer(header='Custom Header')
    """
    if cocina is None:
        cocina = cocinaConfig.init_for_project()
    if name_parts:
        name_parts = safe_join(*name_parts, sep='-')
    printer = Printer(log_dir=cocina.log_dir, header=header, log_name_part=name_parts)
    return cocina, printer


def _process_jobs_and_user_config(jobs: List[str], dry_run: bool) -> Tuple[List[str], Dict[str, Any]]:
    """Process job arguments and user configuration from CLI input.

    Args:
        jobs: List of job names and key=value configuration pairs
        dry_run: Whether to enable dry run mode

    Returns:
        Tuple containing list of job names and processed configuration dict

    Usage:
        >>> jobs, config = _process_jobs_and_user_config(['job1', 'key=value'], True)
        >>> jobs, config = _process_jobs_and_user_config(['job1', 'job2'], False)
    """
    _jobs=[]
    _config=dict(DRY_RUN=dry_run)
    for job in jobs:
        if '=' in job:
            k, v = job.split('=')
            _config[k] = v
        else:
            _jobs.append(job)
    _config = _process_user_config(_config)
    return _jobs, _config


def _process_user_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Process user configuration values with type conversion.

    Args:
        config: Dictionary of configuration key-value pairs

    Returns:
        Processed configuration dictionary with converted values

    Usage:
        >>> result = _process_user_config({'count': '5', 'items': 'a,b,c'})
        >>> result = _process_user_config({'flag': 'true', 'value': '3.14'})
    """
    _config = dict()
    for k, v in config.items():
        if isinstance(v, str):
            if ',' in v:
                v = v.split(',')
                v = [_process_value(x) for x in v if x or (x == 0)]
            else:
                v = _process_value(v)
        _config[k] = v
    return _config


def _process_value(value: str) -> Union[int, float, str]:
    """Convert string value to appropriate numeric type if possible.

    Args:
        value: String value to process and convert

    Returns:
        Converted value as int, float, or original string

    Usage:
        >>> result = _process_value('42')      # Returns: 42 (int)
        >>> result = _process_value('3.14')    # Returns: 3.14 (float)
        >>> result = _process_value('text')    # Returns: 'text' (str)
    """
    try:
        value = float(value)
        if value.is_integer():
            value = int(value)
    except:
        pass
    return value


#
# MAIN
#
cli.add_command(init)
cli.add_command(job)
