Set Cols 80
Set Rows 20

Hide
Source common.setup.tape

# Launch with a new notebook
Type@0 "euporie notebook new.ipynb"
Enter
Wait /ipykernel/

# Enter code into a cell
Enter
Type 'print("Hello from euporie")'
Ctrl+E
Sleep 0.1
Show
Sleep 2

# Open the "Kernel" menu
Alt+k
Sleep 1

# Navigate to "restart kernel" entry
Down
Sleep 1

Down
Sleep 1

Enter
Sleep 1
Type@0 "[<0;380;245M"
Sleep 0.5
Type@0 "[<0;380;245m"

Wait /○/
Sleep 4s
