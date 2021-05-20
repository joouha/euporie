# -*- coding: utf-8 -*-
"""Nox sessions."""
from __future__ import annotations

import nox  # type: ignore
from nox_poetry import Session, session  # type: ignore

package = "euporie"
python_versions = ["3.9", "3.8"]
nox.options.sessions = "lint", "safety", "mypy", "pytype"
locations = "euporie", "tests", "scripts"


@session(python=python_versions[0])
def format(session: "Session") -> None:
    """Run black and isort code formatters."""
    args = session.posargs or locations
    session.install("black", "isort")
    session.run("black", *args)
    session.run("isort", *args)


@session(python=python_versions)
def lint(session: "Session") -> "None":
    """Lint using flake8."""
    args = session.posargs or locations
    session.install(
        "flake8",
        "flake8-annotations",
        "flake8-bandit",
        "flake8-black",
        "flake8-bugbear",
        "flake8-docstrings",
        "flake8-isort",
        "darglint",
    )
    session.run("flake8", *args)


@session(python=python_versions[0])
def safety(session: "Session") -> "None":
    """Scan dependencies for insecure packages."""
    requirements = session.poetry.export_requirements()
    session.install("safety")
    session.run("safety", "check", "--full-report", f"--file={requirements}")


@nox.session(python=python_versions)
def mypy(session: "Session") -> "None":
    """Type-check using mypy."""
    args = session.posargs or locations
    session.install("mypy", ".")
    session.run("mypy", *args)


@session(python=python_versions[0])
def pytype(session: "Session") -> "None":
    """Type-check using pytype."""
    args = session.posargs or ["--disable=import-error", *locations]
    session.install("pytype", ".")
    session.run("pytype", *args)


# @nox.session(python=["3.9", "3.8"])
# def typeguard(session: "Session") -> None:
# """Runtime type checking using Typeguard."""
# args = session.posargs or ["-m", "not e2e"]
# session.run("poetry", "install", "--no-dev", external=True)
# session.install("pytest", "pytest-mock", "typeguard")
# session.run("pytest", f"--typeguard-packages={package}", *args)
