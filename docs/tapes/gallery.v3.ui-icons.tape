Set Cols 160
Set Rows 40

Hide
Source common.setup.tape

# Launch showing the side-bar so its icons are visible
Type@0 "git clone --depth=1 https://github.com/joouha/euporie"
Enter
Wait+line //
Type@0 "cd euporie/"
Enter
Wait+line //
Type@0 "euporie notebook --show-side-bar"
Enter
Sleep 3s

# Open the "help" menu to show the menu icons
Alt+h
Sleep 2

Screenshot gallery.v3.ui-icons.png
Sleep 2
