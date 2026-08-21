Set Cols 80
Set Rows 20

Hide
Source common.setup.tape

# Launch with a new notebook
Type@0 "euporie notebook --show-side-bar --always-show-tab-bar"
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

# Open command palette from menu
Alt+H
Sleep 0.5
Down
Sleep 0.5
Enter
Sleep 2


Type 'toggle side bar'
Sleep 2
Enter
Sleep 2

# Open with shortcut
Ctrl+Space
Type 'tab bar'
Sleep 2
Enter
Sleep 2

Ctrl+Space
Type 'top bar'
Sleep 2
Enter
Sleep 2

Ctrl+Space
Type 'status bar'
Sleep 2
Enter
Sleep 2

Ctrl+Space
Type 'toggle expand'
Sleep 2
Enter


Sleep 4



