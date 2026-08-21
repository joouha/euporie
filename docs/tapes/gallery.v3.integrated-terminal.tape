Set Cols 160
Set Rows 40

Hide
Source common.setup.tape

# Launch euporie-notebook
Type@0 "euporie notebook"
Enter
Sleep 2s

# Show the sidebar but hide any open panels
Alt+:
Sleep 0.5
Type@0 'set-show-side-bar True'
Enter
Sleep 0.5
Alt+:
Sleep 0.5
Type@0 'set-side-bar-panel-index -1'
Enter
Sleep 0.5

# Open a new terminal
Alt+:
Sleep 0.5
Type@0 'new-terminal'
Enter
Sleep 1

# Run a command in the terminal
Type@0 'echo "Hello from the integrated terminal"'
Enter
Enter
Sleep 1
Type@0 'euporie --help'
Enter
Enter
Sleep 2
Type@0 'euporie notebook --version'
Enter
Sleep 1

# Open a new notebook (right side)
Alt+:
Sleep 0.5
Type@0 'new-notebook'
Enter
Sleep 1

# Run some commands in the notebook
Enter
Type@0 'from IPython.display import Image'
Enter
Type@0 'import urllib.request'
Enter
Type@0 'Image(urllib.request.urlopen("https://www.python.org/static/img/python-logo.png").read())'
Home
Ctrl+E
Sleep 1
Up

# Open a new console stacked below the notebook on the right
Alt+:
Sleep 0.5
Type@0 'new-console'
Enter
Sleep 1
# Tile the open tabs
Alt+:
Sleep 0.5
Type@0 'tile-tabs'
Enter
Sleep 1


# Run some commands in the console
Type@0 'from matplotlib import pyplot as plt'
Enter
Sleep 2
Type@0 'fig, ax = plt.subplots(figsize=(5,2))'
Shift+Enter
Type@0 'ax.plot([1,2,3,4,5,6,7],[98,67,12,34,21,56,78])'
Shift+Enter
Type@0 'plt.show()'
Enter
Sleep 1

Ctrl+pagedown
Ctrl+pagedown
Sleep 2

Screenshot gallery.v3.integrated-terminal.png
Sleep 2
