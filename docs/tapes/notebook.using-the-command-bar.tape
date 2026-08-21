Set Cols 80
Set Rows 20

Hide
Source common.setup.tape

# Launch with a new notebook
Type@0 "euporie notebook --no-show-side-bar --side-bar-index=None --no-always-show-tab-bar --expand --no-show-status-bar --no-show-top-bar"
Enter
Sleep 2s
Ctrl+B
Ctrl+N
Sleep 2s
# Enter code into a cell
Enter
Type@0 'print("Hello from euporie")'
Ctrl+E
Sleep 0.1
Up
Show
Sleep 2

Type ':toggle-show-side-bar'
Sleep 2
Enter
Sleep 2

Type ':toggle-always-show-tab-bar'
Sleep 2
Enter
Sleep 2

Type ':toggle-show-top-bar'
Sleep 2
Enter
Sleep 2

Type ':toggle-show-status-bar'
Sleep 2
Enter
Sleep 2

Type ':toggle-expand'
Sleep 2
Enter
Sleep 2

Sleep 4



