# pypants

[![](https://img.shields.io/pypi/v/pypants.svg)](https://pypi.org/pypi/pypants/) [![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

CLI for working with Python packages and BUILD files in a [Pants](https://www.pantsbuild.org/) monorepo.

Features:

- Auto-generate BUILD files based on the package type and import statements
- Generate new Python package folders through an interactive CLI
- Compute a topologically-sorted list of dependencies for a given Python build target

Table of Contents:

- [Installation](#installation)
- [Guide](#guide)
  - [Commands](#commands)
  - [Project Configuration](#project-configuration)
  - [Package Configuration](#package-configuration)
  - [Package Types](#package-types)
  - [Registering Extra Targets](#registering-extra-targets)
  - [Package Generators](#package-generators)

## Installation

pypants requires Python 3.6 or above

```bash
pip install pypants
```

## Guide

### Commands

#### `pypants process-requirements`

Update `3rdparty/python/import-map.json` using the entries in `3rdparty/python/requirements.txt`. All this does is convert the published package name to an import name. Execute this command when you add a new requirement to `requirements.txt`.

#### `pypants process-packages`

Auto-generate all relevant BUILD files in the project/repo. You should execute this command in a git pre-commit or pre-push hook so your BUILD files are kept up to date. You can also run it on demand after you add a new dependency to an internal package.

#### `pypants generate-package`

Starts an interactive CLI that generates a new package folder. This depends on the package generators you registered.

### Project Configuration

To configure your project, add a file named `.pypants.cfg` to the root of your Git repo and paste the example below. You should define the `top_dirs` option at a minimum.

```ini
[project]

; **************
; COMMON OPTIONS
; **************

; REQUIRED: Top-level directories to search for Python packages. These are relative
; to your project/repo root. This is a JSON list of strings.
top_dirs = ["."]

; Prefix to use for names of packages generated by pypants. e.g. foobar_
; python_package_name_prefix =

; Never look for or process files in these directories. This is a JSON list of
; strings. e.g. ["node_modules", "generators"]
; ignore_dirs = []

; ****************
; UNCOMMON OPTIONS
; ****************

; Set of target package names to ignore when collecting build targets. This is a
; JSON list of strings.
; ignore_targets = []

; Path to the location of the import-map.json file relative to the project root
; third_party_import_map_path = 3rdparty/python/import-map.json

; Path to the requirements.txt relative to the project root. The default value is
; the default that Pants uses.
; third_party_requirements_path = 3rdparty/python/requirements.txt
```

Besides the JSON lists, other options are parsed with Python's built-in [ConfigParser](https://docs.python.org/3/library/configparser.html).

### Package Configuration

`pypants` currently expects the Python package to be structured like:

```txt
mypackage/
├── setup.py
├── .pypants.cfg <---- this is the pypants config file
├── src/
    ├── BUILD <---- pypants will generate this file
    ├── mypackage/
        ├── __init__.py
        ├── ...source code...
├── tests/
    ├── unit/
        ├── BUILD <---- pypants will generate this file
        ├── ...unit tests...
    ├── functional/
        ├── BUILD <---- pypants will generate this file
        ├── ...functional tests...
```

To configure each package, add a file named `.pypants.cfg` to the package folder and paste the example below. You should define the `type` option at a minimum.

```ini
[package]

; **************
; COMMON OPTIONS
; **************

; REQUIRED: Package type. See Package Types section for available values.
type = library

; ****************
; UNCOMMON OPTIONS
; ****************

; Extra set of dependencies to include in the python_library target. This is a
; JSON list of strings.
; extra_dependencies = []

; Extra set of tags to include in the Pants build targets. This is a JSON list of
; strings.
; extra_tags = []

; Flag denoting whether to generate a BUILD file.
; generate_build_file = true

; Flag denoting whether to generate a python_binary target for local.py. This is
; essentially an extra entry point. It's only used for specific package types.
; generate_local_binary = false

; Flag denoting whether to include a python_binary target for pytest
; generate_pytest_binary = false

; Flag denoting whether to include a coverage attribute on pytest targets
; include_test_coverage = true
```

### Package Types

Each of the package types will result in a different BUILD file.

#### `library`

The BUILD file for internal Python libraries has one target defined. For example:

```python
python_library(
    dependencies=[
        "3rdparty/python:arrow",
        "3rdparty/python:isoweek",
        "lib/code/src",
        "lib/logger/src",
    ],
    sources=globs("my_library/**/*"),
    tags={"code", "lib", "python"},
)
```

There is no name provided so this target can be referenced just by its containing folder path. In this case it would be `"<TOPDIR>/my_library/src"`.

#### `binary`

A binary target can be used for executable scripts (CLIs and servers) and usually depend on internal libraries. The BUILD has a library and binary target defined:

```python
python_library(
    name="lib",
    dependencies=[
        "3rdparty/python:boto3",
        "3rdparty/python:cfn-flip",
        "3rdparty/python:Click",
        "3rdparty/python:jsonschema",
        "lib/logger/src",
    ],
    sources=globs("cli_deploy/**/*"),
    tags={"apps", "code", "python"},
)
python_binary(
    name="deploy",
    dependencies=[":lib"],
    source="cli_deploy/cli.py",
    tags={"apps", "code", "python"},
)
```

- The `python_library` target is pretty much the same as an internal Python library package
- The `python_binary` target defines an explicit name. This is because when we go to build the PEX file, we want to define the filename. In this example, running `./pants binary apps/cli_deploy/src:deploy` will result in `dist/deploy.pex`.
- The only dependency for the binary should be the library. The library will then include all the dependencies.
- `source` points to the entry point of the binary. This module should handle the `if __name__ == "__main__"` condition to kick off the script.

#### `test`

pypants looks for subfolders named unit, functional, or component within a package's `tests/` folder. The BUILD file for test folders have a few targets defined. For example:

```python
python_library(
    name="lib/time_utils/tests/unit",
    dependencies=[
        "3rdparty/python:arrow",
        "lib/python_core/src",
        "lib/time_utils/src"
    ],
    sources=globs("**/*"),
    tags={"lib", "python", "tests", "unit"},
)
python_tests(
    dependencies=[":lib/time_utils/tests/unit"],
    sources=globs("**/*.py"),
    tags={"lib", "python", "tests", "unit"},
)
python_binary(
    name="unittest",
    entry_point="unittest",
    dependencies=[":lib/time_utils/tests/unit"]
)
```

- The `python_library` target is mostly here to define the unit tests dependencies in a single place so the other two targets can point to it
- The `python_tests` target lets us run pytest against the test files that match `**/*.py`
- The `python_binary` target lets us run the unittest module directly. We won't actually package up this target via `./pants binary`. Setting the entry_point to `"unittest"` is essentially the same as running `python -m unittest test_something.py` from the command line.

#### `lambda_function`

The BUILD file for the Lambda handler contains a special-purpose build target: `python_awslambda`. This target is a wrapper around [lambdex](https://github.com/wickman/lambdex). It creates a PEX like the `python_binary` target (you can execute it) but it modifies the PEX to work with a Lambda Function. For example:

```python
python_library(
    name="my-lambda-lib",
    sources=globs("lambda_handler/**/*"),
    dependencies=[
        "3rdparty/python:requests",
        "lib/logger/src",
    ],
)
python_binary(
    name="my-lambda-bin",
    source="lambda_handler/lambda_handler.py",
    dependencies=[":my-lambda-lib"],
)
python_awslambda(
    name="my-lambda",
    binary=":my-lambda-bin",
    handler="lambda_handler.lambda_handler:lambda_handler",
)
```

This BUILD file will be placed in the same folder as the `.pypants.cfg` file.

#### `migration`

The BUILD file for an [Alembic](https://alembic.sqlalchemy.org/) migration uses the `python_app` target to include the loose version files:

```python
python_library(
    name="lib",
    dependencies=[
        "3rdparty/python:alembic",
        "3rdparty/python:SQLAlchemy",
        "lib/core/src",
    ],
    sources=globs("**/*"),
    tags={"code", "db", "migration", "python"},
)
python_binary(name="alembic", entry_point="alembic.config", dependencies=[":lib"])
python_app(
    name="migrations-my-database-name",
    archive="tar",
    binary=":alembic",
    bundles=[
        bundle(fileset=globs("alembic.ini")),
        bundle(fileset=globs("env.py")),
        bundle(fileset=globs("versions/*.py")),
    ],
    tags={"code", "db", "migration", "python"},
)
```

This BUILD file will be placed in the same folder as the `.pypants.cfg` file.

#### `behave`

The BUILD file for a [behave](https://behave.readthedocs.io/en/latest/) test package includes a library target with test dependencies and a binary target that wraps behave. For example:

```python
python_library(
    name="lib",
    dependencies=[
        "3rdparty/python:requests",
        "lib/application_config/src",
    ],
    sources=globs("**/*"),
    tags={"integration", "python", "tests", "tests-integration"},
)
python_binary(
    source="behave_cli.py",
    dependencies=[":lib"],
    tags={"integration", "python", "tests", "tests-integration"},
)
```

This BUILD file will be placed in the same folder as the `.pypants.cfg` file.

The `behave_cli.py` source references a wrapper script that you should add to the folder:

```python
"""Programmatic entrypoint to running behave from the command line"""
import os
import sys

from behave.__main__ import main as behave_main

if __name__ == "__main__":
    cwd = os.getcwd()
    os.chdir(os.path.dirname(__file__))
    try:
        exit_code = behave_main(sys.argv[1:])
    finally:
        os.chdir(cwd)
        sys.exit(exit_code)
```

#### `py2sfn_project`

py2sfn is a framework that simplifies the creation and deployment of workflows to [AWS Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html). The BUILD file for a project only includes a generic target with the set of task dependencies:

```python
target(
    dependencies=[
        "stepfunctions/projects/example-project/tasks/lambda_fetchjoke/src:lib",
        "stepfunctions/projects/example-project/tasks/lambda_generatelist/src:lib",
        "stepfunctions/projects/example-project/tasks/lambda_rankcharactersbyjoke/src:lib",
    ],
    tags={"py2sfn-project", "python", "stepfunctions/projects"},
)
```

This BUILD file will be placed in the same folder as the `.pypants.cfg` file.

### Registering Extra Targets

If your project contains internal packages that don't aren't represented cleanly by the `.pypants.cfg` file, you can register extra targets programmatically.

1. In your repo, create a new file at `.pypants/targets.py`
1. Define a top-level function called `register_extra_targets`. Within that function, instantiate your extra build targets and return a dictionary that maps package name to `BuildTarget`.

For example, if you have several Alembic database folders:

```python
"""Module that defines extra pypants build targets"""
from typing import Dict

from pypants.config import PROJECT_CONFIG
from pypants.build_targets import AlembicMigrationPackage


def register_extra_targets() -> Dict[str, "pypants.build_targets.base.PythonPackage"]:
    """Register extra targets specific to MyProject"""
    targets = {}

    # Register task targets for Alembic database migration targets
    #
    # * For migrations, this searches db/ looking for eny.py files. If it finds one,
    #   it means we've found an Alembic migration folder and can register a build
    #   target.
    env_py_paths = PROJECT_CONFIG.config_dir_path.joinpath("db").glob("**/env.py")
    for env_py_path in env_py_paths:
        alias = env_py_path.parent.name.replace("_db", "").replace("_", "-")
        package_name = f"migrations-{alias}"
        target = AlembicMigrationPackage(
            target_type="code",
            build_template="migration",
            top_dir_name="db",
            package_dir_name=env_py_path.parent.name,
            package_path=str(env_py_path.parent),
            package_name=package_name,
            build_dir=str(env_py_path.parent),
            extra_tags={"migration"},
        )
        targets[package_name] = target

    return targets
```

### Package Generators

The `generate-package` command can be used to create a new package on disk. It sources package "generators" (folders that define the package boilerplate) from the `.pypants/generators` folder in your repo. To create a new package generator, copy one of the folders from [`examples/generators/`](examples/generators/) to `<your repo>/.pypants/generators/<name>` and modify it as needed. The generators use a tool called [cookiecutter](https://github.com/cookiecutter/cookiecutter) to rendere templates.
