"""List of 'Tip of the Day' entries for Euporie."""

from __future__ import annotations

from euporie.core.commands import get_cmd


def k(cmd: str) -> str:
    """Shortcut to get formatted key-binding for a command."""
    return get_cmd(cmd).key_str()


TIPS: list[str] = [
    "**Support Euporie Development**<br>"
    "If you find euporie useful, consider starring the project on "
    "GitHub at https://github.com/joouha/euporie to show your support! ⭐️",
    #
    "**Open the Command Palette**<br>"
    f"Press **{k('show-command-palette')}** anywhere to search and run any "
    "available command.",
    #
    "**Run Commands from the Command Bar**<br>"
    "Press `:` to open the command bar, then type a Euporie command name "
    "and press Enter to run it.",
    #
    "**Run Shell Commands**<br>"
    "Press `!` to open the command bar in shell mode, type the shell command "
    "you need, and press Enter to run it without leaving Euporie.",
    #
    "**Format Code Automatically**<br>"
    "Open the top **Settings** menu, choose **Code tools**, then toggle "
    "**Autoformat** to reformat code cells automatically when you run them.",
    #
    "**Preview a Notebook**<br>"
    "Run `euporie-preview notebook.ipynb` to view a rendered notebook in "
    "your terminal.",
    #
    "**Use the Console for Experiments**<br>"
    "Launch `euporie-console` to start an interactive REPL and save the "
    "session as a notebook.",
    #
    "**Toggle Hidden Files**<br>"
    "Enable 'Show Hidden Files' using the command palette to see hidden "
    "files and folders in the file browser.",
    #
    "**Reconnect to an Existing Kernel**<br>"
    "Use `--connection-file <path>` to attach to a running kernel instead "
    "of starting a new one.",
    #
    "**Change Color Scheme**<br>"
    "Open the top **Settings** menu, select **Color scheme**, and choose "
    "the palette that best matches your terminal.",
    #
    "**Run Euporie over SSH**<br>"
    "Use `euporie-hub` to host a multi-user environment over SSH.",
    #
    "**Go To Cell by Number**<br>"
    "In a notebook type `:` followed by a number to jump directly to a specific cell.",
    #
    "**Always Show Tab Bar**<br>"
    "Open **Settings → UI Elements** and toggle **Always show tab bar** to "
    "keep the tab bar visible at all times.",
    #
    "**Preview Multiple Notebooks**<br>"
    "Pass several `.ipynb` to `euporie-preview` and use the `--show-filenames` "
    "flag to label them.",
    #
    "**Toggle the Side Bar**<br>"
    f"Press **{k('toggle-side-bar-pane')}** to show or hide the sidebar "
    "(file browser, etc.).",
    #
    "**Toggle UI Elements**<br>"
    "Navigate to **Settings → UI Elements** to switch the status bar, "
    "scroll bar, or tab bar on and off without editing config files.",
    #
    "**Change the Tab Layout**<br>"
    "Use **Tabs → Tab mode** to quickly switch between stacked, tiled "
    "horizontally, or tiled vertically tab layouts.",
    #
    "**Change Color Scheme**<br>"
    "From the top menu bar choose **Settings → Color scheme**, then pick the "
    "preset that best matches your terminal palette.",
    #
    "**Switch Syntax Theme**<br>"
    "Head to **Settings → Syntax highlighting → Syntax theme** and choose "
    "the lexer style that suits your notebook best.",
    #
    "**Restart a Kernel Safely**<br>"
    "Use **Kernel → Restart kernel** to restart the current notebook's kernel "
    "without leaving the Euporie interface.",
    #
    "**Review Keyboard Shortcuts**<br>"
    "Open **Help → Keyboard shortcuts** to browse every registered key "
    "binding in a handy reference dialog.",
    #
    "**Run Every Cell at Once**<br>"
    "Open **Run → Run all cells** to execute the entire notebook in one go.",
    #
    "**Interrupt a Stuck Kernel**<br>"
    "Choose **Kernel → Interrupt kernel** if a computation is taking too long "
    "and you need to halt it safely.",
    #
    "**Change Notebook Kernel**<br>"
    "Use **Kernel → Change kernel** to swap the current notebook to another "
    "available Jupyter kernel.",
    #
    "**Switch Editor Key Bindings**<br>"
    "Head to **Settings → Editor key bindings** and pick Micro, Emacs, or Vi "
    "shortcuts to match your preferred workflow.",
    #
    "**Inspect Recent Logs**<br>"
    "Select **Help → View logs** to open a tab showing Euporie's recent log "
    "output for troubleshooting.",
]
