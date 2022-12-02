"""Modify pre-commit hook to run inside hatch environment."""

import os
from pathlib import Path
from textwrap import dedent


def activate_virtualenv_in_precommit_hooks() -> "None":
    """Activate virtualenv in hooks installed by pre-commit.

    This function patches git hooks installed by pre-commit to activate the
    hatch virtual environment. This allows pre-commit to locate hooks in
    that environment when invoked from git.
    """
    virtualenv = os.environ.get("VIRTUAL_ENV")
    if virtualenv is None:
        return

    hookdir = Path(".git") / "hooks"
    if not hookdir.is_dir():
        return

    bindir = str((Path(virtualenv) / "bin").resolve())

    for hook in hookdir.iterdir():
        if hook.name.endswith(".sample") or not hook.is_file():
            continue

        text = hook.read_text()

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
            PATH="{bindir}:$PATH"
            """
        )

        lines.insert(1, header)
        hook.write_text("\n".join(lines))


if __name__ == "__main__":
    activate_virtualenv_in_precommit_hooks()
