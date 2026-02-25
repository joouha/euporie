#!/usr/bin/env python
"""Prepare a euporie release by bumping version and compiling changelog."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
VERSION_FILE = ROOT / "VERSION"
CHANGELOG_DIR = ROOT / "changelog.d"


def get_version() -> str:
    """Read the current version from the version file.

    Returns:
        The current version string.
    """
    return VERSION_FILE.read_text().strip()


def set_version(version: str) -> None:
    """Write the version to the version file.

    Args:
        version: The version string to write.
    """
    VERSION_FILE.write_text(f"{version}\n")


def item(text: str) -> None:
    """Print a task."""
    sys.stdout.write(f"-> \x1b[1m{text}\x1b[0m\n")


def error(text: str) -> None:
    """Print an error message."""
    sys.stdout.write(f"\n    \x1b[31mError:\x1b[0m {text}\n\n")


def success(text: str) -> None:
    """Print a success message."""
    sys.stdout.write(f"\n\x1b[32m✓ {text}\x1b[0m\n")


def run(*args: str, check: bool = True) -> int:
    """Run a command.

    Args:
        args: Command arguments.
        check: Whether to check the return code.

    Returns:
        The return code.
    """
    result = subprocess.run(args, cwd=ROOT)
    if check and result.returncode != 0:
        error(f"Command failed: {' '.join(args)}")
        sys.exit(1)
    return result.returncode


def has_changelog_fragments() -> bool:
    """Check if there are changelog fragments to compile.

    Returns:
        True if there are fragments.
    """
    if not CHANGELOG_DIR.exists():
        return False
    fragments = [
        f
        for f in CHANGELOG_DIR.iterdir()
        if f.is_file() and not f.name.startswith((".", "_"))
    ]
    return len(fragments) > 0


def bump_version(current: str, bump_type: str) -> str:
    """Calculate the new version based on bump type.

    Args:
        current: The current version string.
        bump_type: One of 'major', 'minor', 'patch', or 'release'.

    Returns:
        The new version string.
    """
    # Remove any suffix like -dev, -rc1, etc.
    base_version = re.split(r"[-+]", current)[0]
    parts = base_version.split(".")

    if len(parts) != 3:
        error(f"Invalid version format: {current}")
        sys.exit(1)

    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    elif bump_type == "release":
        # Just remove the -dev suffix
        return base_version
    else:
        error(f"Unknown bump type: {bump_type}")
        sys.exit(1)


def prepare_release(bump_type: str, skip_changelog: bool = False) -> None:
    """Prepare a release.

    Args:
        bump_type: The type of version bump.
        skip_changelog: Whether to skip changelog compilation.
    """
    current_version = get_version()
    new_version = bump_version(current_version, bump_type)

    sys.stdout.write(
        f"\n\x1b[1mPreparing release: {current_version} → {new_version}\x1b[0m\n\n"
    )

    # Update version
    item(f"Updating version to {new_version}")
    set_version(new_version)

    # Compile changelog
    if not skip_changelog:
        if has_changelog_fragments():
            item("Compiling changelog")
            run("uv", "run", "towncrier", "build", "--yes", "--version", new_version)
        else:
            item("No changelog fragments found, skipping")

    # Stage changes
    item("Staging changes")
    run("git", "add", str(VERSION_FILE))
    run("git", "add", str(ROOT / "CHANGELOG.rst"))
    run("git", "add", str(CHANGELOG_DIR), check=False)

    # Commit
    item("Creating release commit")
    run("git", "commit", "-m", f"Release v{new_version}")

    success(f"Release v{new_version} prepared!")
    sys.stdout.write("\nNext steps:\n")
    sys.stdout.write("  1. Review the changes: git show\n")
    sys.stdout.write("  2. Push to remote: git push\n")
    sys.stdout.write("  3. Publish: python scripts/publish.py\n")
    sys.stdout.write(
        "  4. Bump to dev version: python scripts/release.py post-release\n"
    )


def post_release() -> None:
    """Bump version to next dev version after a release."""
    current_version = get_version()

    # Bump patch and add -dev
    new_version = bump_version(current_version, "patch") + "-dev"

    sys.stdout.write(
        f"\n\x1b[1mPost-release: {current_version} → {new_version}\x1b[0m\n\n"
    )

    item(f"Updating version to {new_version}")
    set_version(new_version)

    item("Staging changes")
    run("git", "add", str(VERSION_FILE))

    item("Creating post-release commit")
    run("git", "commit", "-m", f"Bump version to {new_version}")

    success(f"Version bumped to {new_version}")
    sys.stdout.write("\nDon't forget to push: git push\n")


def main() -> None:
    """Parse arguments and run the appropriate command."""
    parser = argparse.ArgumentParser(description="Prepare a euporie release")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Release command
    release_parser = subparsers.add_parser("release", help="Prepare a release")
    release_parser.add_argument(
        "bump_type",
        choices=["major", "minor", "patch", "release"],
        help="Type of version bump (release just removes -dev suffix)",
    )
    release_parser.add_argument(
        "--skip-changelog",
        action="store_true",
        help="Skip changelog compilation",
    )

    # Post-release command
    subparsers.add_parser("post-release", help="Bump to next dev version")

    args = parser.parse_args()

    if args.command == "release":
        prepare_release(args.bump_type, args.skip_changelog)
    elif args.command == "post-release":
        post_release()


if __name__ == "__main__":
    main()
