""" cli

License:
    BSD, see LICENSE.md
"""
from typing import Optional
from pathlib import Path
from pprint import pprint
import click
from project_kit import constants as c
from project_kit import utils
from project_kit.config_handler import ConfigArgs, PKitConfig
from project_kit.printer import Printer


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
@cli.command(name='init', help='initialize project with .pkit file')
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
        log_dir: Optional[str] = c.PKIT_NOT_FOUND,
        package: Optional[str] = c.PKIT_NOT_FOUND,
        force: bool = False):
    src_pkit_path = Path(__file__).parent.parent / 'dot_pkit'
    dest_pkit_path = PKitConfig.file_path()
    utils.safe_copy_yaml(
        src_pkit_path,
        dest_pkit_path,
        log_dir=log_dir,
        constants_package_name=package,
        force=force)
    print(f'pkit: project initialized ({dest_pkit_path})')
    pkit = PKitConfig.init_for_project()
    pprint(pkit)


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

    # 2. pkit-setup
    pkit, printer = _pkit_printer()
    printer.start(vspace=False)

    # 3. set environment (if provided)
    if env:
        printer.message(f"Setting environment: {env}")
        os.environ[pkit.project_kit_env_var_name] = env

    # 4. run jobs
    for job in jobs:
        execute_job(job, user_config=user_config, printer=printer)

    # 5. complete
    printer.stop(f"Jobs ({utils.safe_join(jobs)}) completed successfully!")


#
# HELPERS
#
def execute_job(job: str, user_config: Optional[dict] = None, printer: Optional[Printer] = None) -> None:
    if printer is None:
        pkit, printer = _pkit_printer()
        printer.start()
    printer.set_header(job)
    try:
        config_args = ConfigArgs(job, user_config=user_config)
        printer.vspace()
        job_module = config_args.import_job_module()
        try:
            job_module.run(config_args, printer=printer)
        except TypeError:
            job_module.run(config_args)
        except AttributeError:
            job_module.main()
    except FileNotFoundError as e:
        printer.stop(f"Job configuration not found", error=e)
        sys.exit(1)
    except ImportError as e:
        printer.stop(f"Failed to import job module", error=e)
        sys.exit(1)
    except AttributeError as e:
        printer.stop(f"Job module missing 'run' function", error=e)
        sys.exit(1)
    except Exception as e:
        printer.stop(f"Job execution failed", error=e)
        sys.exit(1)


#
# INTERNAL
#
def _pkit_printer(
        pkit: Optional[PKitConfig] = None,
        header: str = c.PKIT_CLI_DEFAULT_HEADER) -> PKitConfig:
    """
    FIX ME
    """
    if pkit is None:
        pkit = PKitConfig.init_for_project()
    printer = Printer(log_dir=pkit.log_dir, header=header)
    return pkit, printer


def _process_jobs_and_user_config(jobs, dry_run) -> None:
    """
    FIX ME
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


def _process_user_config(config) -> None:
    """
    FIX ME
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


def _process_value(value) -> None:
    """
    FIX ME
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
