Set Cols 160
Set Rows 40

Hide
Source common.setup.tape

# Launch with a new notebook
Type@0 "euporie notebook --kernel-name=local-python --max-notebook-width=90"
Enter
Sleep 2s
Ctrl+N
Wait /Local Python/
Sleep 500ms

# Open the variable viewer via the command bar
Alt+:
Type@0 'set-show-side-bar True'
Enter
Alt+:
Type@0 'set-side-bar-panel-index 3'
Enter
Alt+:
Type@0 'set-side-bar-width 40'
Enter
Sleep 1

# Define some variables
Enter
Type@0 'x = True'
Enter
Enter
Type@0 'y = 42'
Enter
Enter
Type@0 'name = "euporie"'
Enter
Enter
Type@0 'values = [1, 2, 3, 4, 5]'
Enter
Enter
Type@0 'unique = {"a", "b", "c", "d"}'
Enter
Enter
Type@0 'items = {"A": 100, "B": 200}'
Enter
Enter
Type@0 'def function():'
Enter
Type@0 'raise NotImplemented'
Enter
Backspace
Enter
Type@0 'f = lambda x: x^3 + 2*x^2 - 4*x + 9'
Ctrl+R
Enter
Type@0 'from IPython.display import Image'
Enter
Type@0 'import urllib.request'
Enter
Enter
Type@0 'image = Image(urllib.request.urlopen("https://www.python.org/static/img/python-logo.png").read())'
Enter
Type@0 'image'
Ctrl+E
Wait /○/
Sleep 1
Up

Screenshot gallery.v3.variable-viewer.png
