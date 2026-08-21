Set Cols 80
Set Rows 20

Hide
Source common.setup.tape

# Wait for the prompt, launch the app, let it boot, then capture.
Type@0 "euporie notebook"
Enter
Wait / ⚈ /
Ctrl+n
Wait /ipykernel/
Show
Sleep 1s

Hide
Alt+:
Type@0 'notify "**y** (code cell)" timeout=1 placement=bottom format=markdown extend=False class=info'
Enter
Sleep 0.1
Show
Sleep 1
Enter
Sleep 1
Type 'print("Code cell")'
Sleep 1
Ctrl+E
Sleep 1

Type b
Sleep 1

Hide
Alt+:
Type@0 'notify "**r** (raw cell)" timeout=1 placement=bottom format=markdown extend=False class=info'
Enter
Sleep 0.1
Show
Type r
Sleep 1

Enter
Sleep 1
Type 'Raw cell'
Sleep 1
Ctrl+E
Sleep 1

Type b
Sleep 1

Hide
Alt+:
Type@0 'notify "**m** (markdown cell)" timeout=1 placement=bottom format=markdown extend=False class=info'
Enter
Sleep 0.1
Show
Type m
Sleep 1

Enter
Sleep 1
Type "## Markdown cell"
Enter
Enter
Type '-'
Type '-'
Type '-'
Sleep 1
Ctrl+E
Sleep 1

Sleep 4s
