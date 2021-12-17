"""Command-line interface."""

from pathlib import Path
from typing import List

import click
import pluggy

from . import hookspecs, lib
from .core import TestPackage
from .logger import get_logger
from .report import gen_report
from .schema import EdgetestValidator, Schema
from .utils import (
    gen_requirements_config,
    parse_cfg,
    upgrade_requirements,
    upgrade_setup_cfg,
)

LOG = get_logger(__name__)


def get_plugin_manager() -> pluggy.PluginManager:
    """Get the plugin manager.

    Registers the default ``venv`` plugin.

    Returns
    -------
    PluginManager
        The plugin manager.
    """
    pm = pluggy.PluginManager("edgetest")
    pm.add_hookspecs(hookspecs)
    pm.load_setuptools_entrypoints("edgetest")
    pm.register(lib)

    return pm


@click.command()
@click.option(
    "--config",
    "-c",
    default=None,
    type=click.Path(exists=True),
    help="Path to the test configuration file",
)
@click.option(
    "--requirements",
    "-r",
    default="requirements.txt",
    type=click.Path(),
    help="Path to a requirements file",
)
@click.option(
    "--environment",
    "-e",
    default=None,
    help="Name of a specific environment to run",
)
@click.option(
    "--notest",
    is_flag=True,
    help="Whether or not to run the test command for each environment",
)
@click.option(
    "--nosetup",
    is_flag=True,
    help="Whether or not to only set up the conda environment(s)",
)
@click.option(
    "--extras",
    type=str,
    multiple=True,
    default=None,
    help="List of extra installations for the local package. Only used if using ``requirements``",
)
@click.option(
    "--deps",
    "-d",
    type=str,
    multiple=True,
    default=None,
    help="Additional `pip` dependencies to install. Only used if using ``requirements``.",
)
@click.option(
    "--command",
    type=str,
    default="pytest",
    help="The test command to use in each environment. Only used if using ``requirements``.",
)
@click.option(
    "--export",
    is_flag=True,
    help="Whether or not to export the updated requirements file. Overwrites input requirements.",
)
def cli(
    config,
    requirements,
    environment,
    notest,
    nosetup,
    extras,
    deps,
    command,
    export,
):
    """Create the environments and test.

    If you do not supply a YAML configuration file, this package will search for a
    ``requirements.txt`` file and create a conda environment for each package in that file.
    """
    # Get the hooks
    pm = get_plugin_manager()
    if config:
        conf = parse_cfg(filename=config, requirements=requirements)
    else:
        # Find the path to the local directory using the requirements file
        conf = gen_requirements_config(
            fname_or_buf=requirements,
            extras=extras,
            deps=deps,
            command=command,
            package_dir=str(Path(requirements).parent),
        )

    # Validate the configuration file
    docstructure = Schema()
    pm.hook.addoption(schema=docstructure)
    validator = EdgetestValidator(schema=docstructure.schema)
    if not validator.validate(conf):
        click.echo("Unable to validate configuration file.")
        raise ValueError("Unable to validate configuration file.")
    conf = validator.document

    if environment:
        conf["envs"] = [env for env in conf["envs"] if env["name"] == environment]

    # Run the pre-test hook
    pm.hook.pre_run_hook(conf=conf)
    testers: List[TestPackage] = []
    for env in conf["envs"]:
        testers.append(
            TestPackage(
                hook=pm.hook,
                envname=env["name"],
                upgrade=env["upgrade"],
                package_dir=env["package_dir"],
            )
        )
        # Set up the test environment
        if nosetup:
            click.echo(f"Using existing environment for {env['name']}...")
        else:
            testers[-1].setup(**env)
        # Run the tests
        if notest:
            click.echo(f"Skipping tests for {env['name']}")
        else:
            testers[-1].run_tests(env["command"])

    report = gen_report(testers)
    click.echo(f"\n\n{report}")

    if export and testers[-1].status:
        if config is not None and Path(config).name == "setup.cfg":
            parser = upgrade_setup_cfg(
                upgraded_packages=testers[-1].upgraded_packages(),
                filename=config,
            )
            with open(config, "w") as outfile:
                parser.write(outfile)
            if "options" not in parser or not parser.get("options", "install_requires"):
                click.echo(
                    "No PEP-517 style requirements in ``setup.cfg`` to update. Updating "
                    f"{requirements}"
                )
                upgraded = upgrade_requirements(
                    fname_or_buf=requirements,
                    upgraded_packages=testers[-1].upgraded_packages(),
                )
                with open(requirements, "w") as outfile:
                    outfile.write(upgraded)
        else:
            click.echo(f"Overwriting the requirements file {requirements}...")
            upgraded = upgrade_requirements(
                fname_or_buf=requirements,
                upgraded_packages=testers[-1].upgraded_packages(),
            )
            with open(requirements, "w") as outfile:
                outfile.write(upgraded)

    # Run the post-test hook
    pm.hook.post_run_hook(testers=testers, conf=conf)
