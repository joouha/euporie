# -*- coding: utf-8 -*-
"""Nox sessions."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nox
from nox_poetry import Session, session

package = "euporie"
python_versions = ["3.10", "3.9", "3.8"]
nox.options.sessions = "format_check", "lint", "safety", "tests", "mypy", "pytype"
locations = [
    "euporie/core",
    "euporie/console",
    "euporie/notebook",
    "euporie/preview",
    "euporie/hub",
    "tests",
    "scripts",
]


def activate_virtualenv_in_precommit_hooks(session: "Session") -> "None":
    """Activate virtualenv in hooks installed by pre-commit.

    This function patches git hooks installed by pre-commit to activate the
    session's virtual environment. This allows pre-commit to locate hooks in
    that environment when invoked from git.

    Args:
        session: The Session object.

    """
    if session.bin is None:
        return

    virtualenv = session.env.get("VIRTUAL_ENV")
    if virtualenv is None:
        return

    hookdir = Path(".git") / "hooks"
    if not hookdir.is_dir():
        return

    for hook in hookdir.iterdir():
        if hook.name.endswith(".sample") or not hook.is_file():
            continue

        text = hook.read_text()
        bindir = repr(session.bin)[1:-1]  # strip quotes
        if not (
            Path("A") == Path("a") and bindir.lower() in text.lower() or bindir in text
        ):
            continue

        lines = text.splitlines()
        if not (lines[0].startswith("#!") and "bash" in lines[0].lower()):
            continue

        header = dedent(
            f"""
            VIRTUAL_ENV="{virtualenv}"
            PATH="{session.bin}:$PATH"
            """
        )

        lines.insert(1, header)
        hook.write_text("\n".join(lines))


@session(name="pre-commit", python=python_versions[0])
def precommit(session: Session) -> None:
    """Lint using pre-commit."""
    args = session.posargs or ["run", "--all-files", "--show-diff-on-failure"]
    session.install(
        "black",
        "isort",
        "ssort",
        "darglint",
        "flake8",
        "flake8-bandit",
        "flake8-black",
        "flake8-bugbear",
        "flake8-docstrings",
        "flake8-annotations",
        "pre-commit",
        "pre-commit-hooks",
        "codespell",
    )
    session.run("pre-commit", *args)
    if args and args[0] == "install":
        activate_virtualenv_in_precommit_hooks(session)


@session(python=python_versions[0])
def format(session: "Session") -> None:
    """Run black and isort code formatters."""
    args = session.posargs or locations
    session.install("black", "isort", "ssort")
    session.run("ssort", *args)
    session.run("isort", "--profile", "black", *args)
    session.run("black", *args)


@session(python=python_versions[0])
def format_check(session: "Session") -> None:
    """Run black and isort code formatters."""
    args = session.posargs or locations
    session.install("black", "isort", "ssort")
    session.run("ssort", "--check", *args)
    session.run("isort", "--profile", "black", "--check", *args)
    session.run("black", "--check", *args)


@nox.session(python=python_versions)
def mypy(session: "Session") -> "None":
    """Type-check using mypy."""
    session.install("mypy", "rich", "black", "isort")
    session.install("-e", ".")
    if session.posargs:
        session.run("mypy", *session.posargs)
    else:
        modules = sum([["-p", path.replace("/", ".")] for path in locations], start=[])
        session.run("mypy", "--namespace-packages", *modules)


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


@session(python=python_versions)
def safety(session: "Session") -> "None":
    """Scan dependencies for insecure packages."""
    requirements = session.poetry.export_requirements()
    session.install("safety")
    session.run("safety", "check", "--full-report", f"--file={requirements}")


# @nox.session(python=["3.9", "3.8"])
# def typeguard(session: "Session") -> None:
# """Runtime type checking using Typeguard."""
# args = session.posargs or ["-m", "not e2e"]
# session.run("poetry", "install", "--no-dev", external=True)
# session.install("pytest", "pytest-mock", "typeguard")
# session.run("pytest", f"--typeguard-packages={package}", *args)


@session(python=python_versions)
def tests(session: "Session") -> "None":
    """Run the test suite."""
    session.install(".")
    session.install(
        "coverage",
        "pytest",
    )

    try:
        session.run("coverage", "run", "--parallel", "-m", "pytest", *session.posargs)
    finally:
        if session.interactive:
            session.notify("coverage", posargs=[])


@session(python=python_versions)
def coverage(session: "Session") -> "None":
    """Produce the coverage report."""
    args = session.posargs or ["report"]

    session.install("coverage[toml]")

    if not session.posargs and any(Path().glob(".coverage.*")):
        session.run("coverage", "combine")

    session.run("coverage", *args)


# Pytype does not support 3.10 yet
@session(python=["3.8", "3.9"])
def pytype(session: "Session") -> "None":
    """Type-check using pytype."""
    args = session.posargs or locations
    session.install("pytype", ".")
    session.run("pytype", *args)
