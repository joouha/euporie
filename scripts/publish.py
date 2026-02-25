#!/usr/bin/env python
"""Publish euporie packages to PyPI."""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
log = logging.getLogger(__name__)

# Package publish order (dependencies first)
PACKAGES = [
    "apptk",
    "euporie-core",
    "euporie-console",
    "euporie-notebook",
    "euporie-preview",
    "euporie-hub",
]

ROOT = Path(__file__).parent.parent


def check_output(*args: str, cwd: Path | None = None) -> str:
    """Check the output of a command.

    Args:
        args: List of words in a command line string.
        cwd: Working directory for the command.

    Returns:
        The stripped stdout of the command.
    """
    return subprocess.check_output(args, text=True, cwd=cwd).strip()


def run(*args: str, cwd: Path | None = None) -> int:
    """Run a command and return the exit code.

    Args:
        args: List of words in a command line string.
        cwd: Working directory for the command.

    Returns:
        The exit code of the command.
    """
    return subprocess.call(args, cwd=cwd)


def item(text: str) -> None:
    """Print a task."""
    sys.stdout.write(f"-> \x1b[1m{text}\x1b[0m\n")


def error(text: str) -> None:
    """Print an error message."""
    sys.stdout.write(f"\n    \x1b[31mError:\x1b[0m {text}\n\n")


def status(value: str) -> None:
    """Print a status field at the end of a line."""
    sys.stdout.write(f"\x1b[1F\x1b[9999C\x1b[{len(value) + 2}D ")
    if value == "FAIL":
        sys.stdout.write("\x1b[31m")
    else:
        sys.stdout.write("\x1b[32m")
    sys.stdout.write(f"{value}\x1b[0m\n")


def get_version() -> str:
    """Read the current version from the version file.

    Returns:
        The current version string.
    """
    version_file = ROOT / "VERSION"
    return version_file.read_text().strip()


def get_package_dir(package: str) -> Path:
    """Get the directory for a package.

    Args:
        package: The package name.

    Returns:
        The path to the package directory.
    """
    return ROOT / "packages" / package


def check_prerequisites() -> bool:
    """Check that required tools are available.

    Returns:
        True if all prerequisites are met.
    """
    item("Checking prerequisites")
    try:
        check_output("uv", "--version")
    except FileNotFoundError:
        status("FAIL")
        error("uv is not installed")
        return False
    status("PASS")
    return True


def check_version(version: str) -> bool:
    """Check that the version number is valid for release.

    Args:
        version: The version string to check.

    Returns:
        True if the version is valid.
    """
    item("Checking version number")
    for key in ("dev", "rc", "alpha", "beta"):
        if key in version:
            status("FAIL")
            error(f"Version contains '{key}': {version}")
            return False
    status("PASS")
    return True


def check_git_state() -> bool:
    """Check that the git repository is in a valid state for release.

    Returns:
        True if the git state is valid.
    """
    item("Checking we are on main branch")
    current_branch = check_output("git", "branch", "--no-color", "--show-current")
    if current_branch != "main":
        status("FAIL")
        error(f"Checked out branch is '{current_branch}', not 'main'")
        return False
    status("PASS")

    item("Checking repo is clean")
    if check_output("git", "status", "--porcelain"):
        status("FAIL")
        error("Git repository is not clean")
        return False
    status("PASS")

    item("Checking for remote changes")
    check_output("git", "fetch", "--all")
    if check_output("git", "log", "HEAD..origin/main", "--oneline"):
        status("FAIL")
        error("Git repository is not up-to-date")
        return False
    status("PASS")

    return True


def check_tag_not_exists(version: str) -> bool:
    """Check that the git tag does not already exist.

    Args:
        version: The version string.

    Returns:
        True if the tag does not exist.
    """
    git_tag = f"v{version}"
    item("Checking version does not yet exist in git")
    if git_tag in check_output("git", "tag").split("\n"):
        status("FAIL")
        error(f"Tag '{git_tag}' already exists")
        return False
    status("PASS")
    return True


def clean_dist() -> bool:
    """Clean the dist directory.

    Returns:
        True on success.
    """
    item("Cleaning dist folder")
    dist_dir = ROOT / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(exist_ok=True)
    status("PASS")
    return True


def build_packages() -> bool:
    """Build all packages.

    Returns:
        True if all packages built successfully.
    """
    for package in PACKAGES:
        item(f"Building {package}")
        package_dir = get_package_dir(package)
        if not package_dir.exists():
            status("FAIL")
            error(f"Package directory not found: {package_dir}")
            return False

        result = run("uv", "build", "--out-dir", str(ROOT / "dist"), cwd=package_dir)
        if result != 0:
            status("FAIL")
            error(f"Failed to build {package}")
            return False
        status("PASS")

    # Build the root meta-package
    item("Building euporie meta-package")
    result = run("uv", "build", "--out-dir", str(ROOT / "dist"), cwd=ROOT)
    if result != 0:
        status("FAIL")
        error("Failed to build euporie meta-package")
        return False
    status("PASS")

    return True


def check_builds() -> bool:
    """Check all built packages with twine.

    Returns:
        True if all packages pass twine check.
    """
    item("Checking builds with twine")
    result = run("uvx", "twine", "check", str(ROOT / "dist" / "*"))
    if result != 0:
        status("FAIL")
        error("Twine check failed")
        return False
    status("PASS")
    return True


def create_and_push_tag(version: str) -> bool:
    """Create and push the git tag.

    Args:
        version: The version string.

    Returns:
        True on success.
    """
    git_tag = f"v{version}"

    item("Creating git tag")
    check_output("git", "tag", "-a", git_tag, "-m", f"Release version {version}")
    status("PASS")

    item("Pushing tag to server")
    check_output("git", "push", "--tags", "-q")
    status("PASS")

    return True


def publish_packages() -> bool:
    """Publish all packages to PyPI.

    Returns:
        True if all packages published successfully.
    """
    item("Uploading to PyPI")
    result = run(
        "uvx",
        "twine",
        "upload",
        "--non-interactive",
        str(ROOT / "dist" / "*"),
    )
    if result != 0:
        status("FAIL")
        error("Failed to upload to PyPI")
        return False
    status("PASS")
    return True


def main() -> bool:
    """Check, build and publish all packages.

    Returns:
        True if the release was successful.
    """
    version = get_version()
    sys.stdout.write(f"\n\x1b[1mReleasing euporie v{version}\x1b[0m\n\n")

    checks = [
        lambda: check_prerequisites(),
        lambda: check_version(version),
        lambda: check_git_state(),
        lambda: check_tag_not_exists(version),
        lambda: clean_dist(),
        lambda: build_packages(),
        lambda: check_builds(),
        lambda: create_and_push_tag(version),
        lambda: publish_packages(),
    ]

    for check in checks:
        if not check():
            return False

    sys.stdout.write(f"\n\x1b[32m✓ Successfully released euporie v{version}\x1b[0m\n")
    return True


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
