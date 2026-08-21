Source setup.tape

Set Cols 80
Set Rows 20

Hide
Source common.setup.tape

# Launch with a new notebook
Type@0 "euporie notebook new.ipynb"
Enter
Wait /○/

# Enter code into a cell
Enter
Type@0 'import sys'
Enter
Type@0 'print(sys.version)'
Sleep 0.1
Ctrl+E
Wait /○/
Up

Show
Sleep 2

# Open the "Kernel" menu
Alt+k
Sleep 1

# Navigate to "restart kernel" entry
Down
Sleep 0.5
Down
Sleep 0.5
Down
Sleep 0.5
Enter
Sleep 1

# Select PyPy
Shift+Tab
Sleep 1
Down
Sleep 1
Tab
Sleep 1
Type@0 "[<0;388;353M"
Sleep 0.5
Type@0 "[<0;388;353m"
Sleep 0.1
Wait /○/
Sleep 1

Ctrl+E
Wait /○/
Sleep 4s
