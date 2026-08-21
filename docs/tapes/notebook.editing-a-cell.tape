Set Cols 80
Set Rows 20

Hide
Source common.setup.tape

# Launch with a new notebook
Type@0 "euporie notebook"
Enter
Sleep 2s
Ctrl+n
Sleep 1s

Show
Sleep 2s

# Entry edit mode
Hide
Hide
Alt+:
Type@0 'notify "**Enter** (enter edit mode)" timeout=1 placement=bottom format=markdown extend=False class=info'
Enter
Sleep 0.1
Show
Sleep 0.25
Enter
Sleep 1s

Type 'print("Hello from euporie!")'
Sleep 1s

Hide
Alt+:
Type@0 'notify "**Escape** (exit edit mode)" timeout=1 placement=bottom format=markdown extend=False class=info'
Enter
Sleep 0.1
Show
Sleep 0.25
Escape
Sleep 4
