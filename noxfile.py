# -*- coding: utf-8 -*-
"""Nox sessions."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nox  # type: ignore
from nox_poetry import Session, session  # type: ignore

package = "euporie"
python_versions = ["3.9", "3.8"]
nox.options.sessions = "lint", "safety", "mypy", "pytype"
locations = "euporie", "tests", "scripts"


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
        if not (lines[0].startswith("#!") and "python" in lines[0].lower()):
            continue

        header = dedent(
            f"""\
            import os
            os.environ["VIRTUAL_ENV"] = {virtualenv!r}
            os.environ["PATH"] = os.pathsep.join((
                {session.bin!r},
                os.environ.get("PATH", ""),
            ))
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
        "darglint",
        "flake8",
        "flake8-bandit",
        "flake8-black",
        "flake8-bugbear",
        "flake8-docstrings",
        "flake8-annotations",
        "pre-commit",
        "pre-commit-hooks",
    )
    session.run("pre-commit", *args)
    if args and args[0] == "install":
        activate_virtualenv_in_precommit_hooks(session)


@session(python=python_versions[0])
def format(session: "Session") -> None:
    """Run black and isort code formatters."""
    args = session.posargs or locations
    session.install("black", "isort")
    session.run("black", *args)
    session.run("isort", "--profile", "black", *args)


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
