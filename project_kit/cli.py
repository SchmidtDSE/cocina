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


#
# CLI INTERFACE
#
@click.group
@click.pass_context
def cli(ctx):
    ctx.obj = {}


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

@cli.command(name='job', help='job help text')
@click.argument('job', type=str)
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
        job: str,
        env: Optional[str] = None,
        verbose: bool = True,
        dry_run: bool = False):

    print('TODO: ADD USER-ARGS?')

    pkit = PKitConfig.init_for_project()
    printer = Printer(f'pkit.job.{job}', log_dir=pkit.log_dir)
    printer.start(vspace=False)
    pkit = PKitConfig.init_for_project()
    # Set environment if provided
    if env:
        printer.message(f"Setting environment: {env}")
        os.environ[pkit.project_kit_env_var_name] = env
    try:
        # Load job configuration and execute
        printer.message(f"🚀 Starting job: {job}")
        ca = ConfigArgs(job)
        job_module = ca.import_job_module()
        # Execute the job
        try:
            job_module.run(ca, printer=printer)
        except:
            job_module.run(ca)
        printer.stop("✅ Job completed successfully!")
    except FileNotFoundError as e:
        printer.stop(f"❌ Job configuration not found: {e}", err=True)
        sys.exit(1)
    except ImportError as e:
        printer.stop(f"❌ Failed to import job module: {e}", err=True)
        sys.exit(1)
    except AttributeError as e:
        printer.stop(f"❌ Job module missing 'run' function: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        printer.stop(f"❌ Job execution failed: {e}", err=True)
        sys.exit(1)

#
# HELPERS
#
# def _process_jobs_and_user_config(jobs, dry_run):
#     _jobs=[]
#     _config=dict(DRY_RUN=dry_run)
#     for job in jobs:
#         if '=' in job:
#             k, v = job.split('=')
#             _config[k] = v
#         else:
#             _jobs.append(dict(name=job))
#     _config = _process_user_config(_config)
#     return _jobs, _config


# def _process_job_options(config, run, jobs, start, end, name):
#     if run and (not config):
#         config = run
#     if name:
#         jobs = start_index = end_index = None
#     elif start:
#         start_index = int(start) - 1
#         if end:
#             end_index = int(end) - 1
#             if end_index <= start_index:
#                 err = (
#                     'tap.cli._process_job_options: '
#                     '<end> must be greater than <start>'
#                 )
#                 raise ValueError(err)
#         else:
#             end_index = start_index
#         jobs = name = None
#     else:
#         start_index = end_index = name = None
#     return config, jobs, name, start_index, end_index


# def _process_user_config(config):
#     _config = dict()
#     for k, v in config.items():
#         if isinstance(v, str):
#             if ',' in v:
#                 v = v.split(',')
#                 v = [_process_value(x) for x in v if x or (x == 0)]
#             else:
#                 v = _process_value(v)
#         _config[k] = v
#     return _config


# def _process_value(value):
#     try:
#         value = int(value)
#     except:
#         try:
#             value = float(value)
#         except:
#             pass
#     return value



#
# MAIN
#
cli.add_command(init)
cli.add_command(job)
