#!/usr/bin/env python
"""Publish euporie to PyPi."""

import logging
import shutil
import subprocess
import sys

# from pip._vendor.rich import error


logging.basicConfig(level=logging.INFO, stream=sys.stdout)
log = logging.getLogger(__name__)


def check_output(*args: "str") -> "str":
    """Check the output of a command.

    Args:
        args: List of works in a command line string
    """
    return subprocess.check_output(args, text=True).strip()


def item(text: "str") -> "None":
    """Print a task."""
    sys.stdout.write(f"-> \x1b[1m{text}\x1b[0m\n")


def error(text: "str") -> "None":
    """Print an error message."""
    sys.stdout.write(f"\n    \x1b[31mError:\x1b[0m {text}\n\n")


def status(value: "str") -> "None":
    """Print a status field at the end of a line."""
    sys.stdout.write(f"\x1b[1F\x1b[9999C\x1b[{len(value) + 2}D ")
    if value == "FAIL":
        sys.stdout.write("\x1b[31m")
    else:
        sys.stdout.write("\x1b[32m")
    sys.stdout.write(f"{value}\x1b[0m\n")


def main() -> "bool":
    """Check, build and publish."""
    from euporie.core import __version__ as version

    item("Checking version number")
    for key in ("dev", "rc"):
        if key in version:
            status("FAIL")
            error(f"Version contains {key}: {version}")
            return False
    status("PASS")

    item("Checking we are on main branch")
    if (
        current_branch := check_output("git", "branch", "--no-color", "--show-current")
    ) != "main":
        status("FAIL")
        error(f"Checked out branch is '{current_branch}', not 'main'")
        return False
    status("PASS")

    item("Checking repo is clean")
    if check_output("git", "status", "--porcelain"):
        status("FAIL")
        error("Git repository is not clean.")
        return False
    status("PASS")

    item("Check for remote changes")
    check_output("git", "fetch", "--all")
    if check_output("git", "log", "HEAD..origin/main", "--oneline"):
        status("FAIL")
        error("Git repository is not up-to-date")
        return False
    status("PASS")

    item("Cleaning build folder")
    shutil.rmtree("./dist")
    status("PASS")

    item("Building package")
    check_output("hatch", "build")
    status("PASS")

    item("Checking build with twine")
    if "ERROR" in check_output("uvx", "twine", "check", "dist/*.*"):
        status("FAIL")
        error("Twine check failed")
        return False
    status("PASS")

    git_tag = f"v{version}"

    item("Checking version does not yet exist in git")
    if git_tag in check_output("git", "tag").split("\n"):
        status("FAIL")
        error(f"Tag `{git_tag}` already exists")
        return False
    status("PASS")

    item("Creating git tag")
    check_output("git", "tag", "-a", git_tag, "-m", f"Release version {version}")
    status("PASS")

    item("Push tag to server")
    check_output("git", "push", "--tags", "-q")
    status("PASS")

    item("Upload to PyPi")
    check_output("hatch", "publish", "-u", "__token__")
    status("PASS")

    return True


if __name__ == "__main__":
    main()
