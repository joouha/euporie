Set Cols 80
Set Rows 20

Hide
Source common.setup.tape

# Launch with a new notebook and setup
Type@0 "euporie notebook" 
Enter
Sleep 2
Ctrl+N
Wait /○/
Sleep 500ms
Enter
Type@0 'print("Hello from euporie")'
Ctrl+E
Sleep 0.2s
Up
Sleep 0.2s
Type@0 ":open my-notebook.ipynb"
Enter
Wait /○/
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
Sleep 3
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
Down
Sleep 0.5
Down
Sleep 0.5
Enter

Sleep 1
Tab
Sleep 1
Enter

Sleep 4s
