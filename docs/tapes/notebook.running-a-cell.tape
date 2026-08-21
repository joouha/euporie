
Set Cols 80
Set Rows 20

Hide
Source common.setup.tape

# Launch with a new notebook
Type@0 "euporie notebook new.ipynb"
Enter
Sleep 2s
# Enter code into a cell
Enter
Type@0 'print("Hello from euporie")'
Escape
Wait /○/

Show
Sleep 2

# Open the "run" menu
Alt+r
Sleep 1

# Navigate to "run cell" entry
Down
Sleep 1
Enter
Wait /○/

Sleep 4s
