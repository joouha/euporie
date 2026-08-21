Set Cols 80
Set Rows 20

Hide
Source common.setup.tape

# Launch with a new notebook and setup
Type@0 "euporie notebook" 
Enter
Sleep 2
Ctrl+N
Sleep 500ms
Type ":open my-notebook.ipynb"
Enter
Sleep 1s
Sleep 1
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
Type a
Enter
Type@0 '# New cell above'
Escape
Down
Type b
Enter
Type@0 '# New cell below'
Sleep 100ms
Escape
Sleep 100ms
Home
Show
Sleep 2

Alt+f
Sleep 0.5
Down
Sleep 0.5
Down
Sleep 0.5
Down
Sleep 0.5
Enter
Wait /   my-notebook.ipynb/

Sleep 4s
