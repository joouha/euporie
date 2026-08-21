Set Cols 80
Set Rows 20

Hide
Source common.setup.tape

# Launch
Type@0 "euporie notebook my-notebook.ipynb" 
Enter
Wait /ipykernel/
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
Sleep 0.1
Ctrl+E
Sleep 2
Ctrl+S
Sleep 2
Ctrl+W
Sleep 0.1
Ctrl+n
Sleep 1
Wait /○/
Enter
Type@0 'print("Hello from euporie")'
Ctrl+e
Home
Sleep 0.2s
Show
Sleep 2

# Open the "file" menu
Alt+f
Sleep 1

# Navigate to "open file" entry
Down
Sleep 1
Down
Sleep 1
Enter
Sleep 1

# Enter notebook name
Type my-notebook.ipynb
Sleep 0.1
Sleep 1

# Navigate dialog
Enter
Sleep 1

Tab
Sleep 1

Hide
Alt+O
Sleep 0.1
Type@0 "[6;5~"
Type@0 "[6;5~"
Sleep 0.1
Show
Sleep 1
Sleep 4s
