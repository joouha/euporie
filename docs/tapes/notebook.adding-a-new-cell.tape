Set Cols 80
Set Rows 20

# Set TypingSpeed 0

Hide
Source common.setup.tape

# Launch with a new notebook
Type@0 "euporie notebook" 
Enter
Sleep 2
Ctrl+N
Wait /ipykernel/
Sleep 500ms
Enter
Type@0 'print("Hello from euporie")'
Ctrl+E
Sleep 0.2s
Up
Sleep 0.2s
Type@0 ":open my-notebook.ipynb"
Enter
Sleep 1s
Enter
Type@0 'print("Hello world!")'
Ctrl+R
Sleep 0.1
Enter
Type@0 '# This is a comment'
Enter
Type@0 'print("This notebook is running in euporie notebook")'
Home
Ctrl+R
Sleep 0.1
Type m
Enter
Type@0 'A _markdown_ cell'
Enter
Type@0 '> Quote'
Enter
Type@0 '- List'
Enter
Type@0 '- Item'
Ctrl+R
Type m
Enter
Type@0 'Another cell'
Sleep 1
Ctrl+E
Home
Ctrl+S
Sleep 1
Show
Sleep 2s

# Add cell above
Hide
Alt+:
Type@0 'notify "**a** (add cell above)" timeout=1 placement=bottom format=markdown extend=False class=info'
Enter
Sleep 0.1
Show
Sleep 0.25
Type a
Sleep 1
Enter
Sleep 1
Type '# New cell above'
Sleep 1
Escape
Sleep 1

# Nav down
Down
Sleep 1

# Add cell below
Hide
Alt+:
Type@0 'notify "**b** (add cell below)" timeout=1 placement=bottom format=markdown extend=False class=info'
Enter
Sleep 0.1
Show
Sleep 0.25
Type b
Sleep 1
Enter
Sleep 1
Type '# New cell below'
Sleep 1
Escape
Sleep 1

Sleep 4s
