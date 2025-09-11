# Project Kit

Project Kit (PKIT) is a collection of tools for building out python projects. PKIT contains:

1. a config_handler: used for mangaing constants and configuation for python projects
2. a runner: used for cleanly executing a sequence of script steps
3. a config_interface: decorator that passes args in configuration files to python methods
4. utilities such as timers and custom loggers

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

Usage example

---

## DOCUMENTATION

API Docss

---

## STYLE-GUIDE

Following PEP8. See [setup.cfg](./setup.cfg) for exceptions. Keeping honest with `pycodestyle .`
