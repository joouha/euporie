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
Type@0 ":open my-notebook.ipynb"
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


# nav down
Hide
Alt+:
Type@0 'notify "**Down** (next cell)" timeout=1 placement=bottom format=markdown extend=False class=info'
Enter
Show
Sleep 0.25
Down
Sleep 1
Down
Sleep 1
Down
Sleep 1
Down
Sleep 1
Down
Sleep 2

# screll up
Hide
Alt+:
Type@0 'notify "**[** (scroll up)" timeout=1 placement=bottom format=markdown extend=False class=info'
Enter
Show
Sleep 0.25
Type '['
Sleep 0.5
Type '['
Sleep 0.5
Type '['
Sleep 0.5
Type '['
Sleep 0.5
Type '['
Sleep 0.5
Type '['
Sleep 0.5
Type '['
Sleep 0.5
Type '['
Sleep 0.5
Type '['
Sleep 0.5
Type '['
Sleep 0.5
Type '['
Sleep 0.5
Type '['
Sleep 0.5
Type '['
Sleep 2

# page down
Hide
Alt+:
Type@0 'notify "**}** (page down)" timeout=1 placement=bottom format=markdown extend=False class=info'
Enter
Show
Sleep 0.25
Type '}'
Sleep 0.5
Type '}'
Sleep 0.5
Type '}'
Sleep 2

Hide
Hide
Alt+:
Type@0 'notify "**Home** (page top)" timeout=1 placement=bottom format=markdown extend=False class=info'
Enter
Show
Sleep 0.25
Home
Sleep 2

Hide
Hide
Alt+:
Type@0 'notify "**End** (page bottom)" timeout=1 placement=bottom format=markdown extend=False class=info'
Enter
Show
Sleep 0.25
End

Sleep 4s
