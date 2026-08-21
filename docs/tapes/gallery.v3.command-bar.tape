Set Cols 160
Set Rows 40

Hide
Source common.setup.tape

# Launch with a new notebook
Type@0 "euporie notebook"
Enter
Sleep 2s
Ctrl+N
Sleep 1s

# Add a second markdown cell describing the command bar
Type@0 'm'
Sleep 0.5
Enter
Type@0 '## Command Bar'
Enter
Enter
Type@0 'The command bar lets you run any registered command by name.'
Enter
Enter
Type@0 'Open it with `:` (or `Alt-:`), type a command or type to search, and use `Tab` to cycle through completions. Press `Enter` to run the selected command.'
Enter
Enter
Type@0 'You can pass arguments after the command name, e.g. `goto-line 10`, or keyword arguments like `set-color-scheme scheme=dark`.'
Sleep 0.1
Ctrl+R
Sleep 1

Enter
Type@0 'print("Command bar demo")'
Sleep 0.1
Ctrl+E
Wait /○/
Sleep 1

# Move back to the top of the notebook
Home
Up

# Customize
Sleep 0.1
Type@0 ':set-custom-foreground-color #e3e1e4'
Enter
Sleep 0.1
Type@0 ':set-custom-background-color #2d2a2e'
Enter
Sleep 0.1
Type@0 ':set-accent-color #fa5e84'
Enter
Sleep 0.1
Type@0 ':set-background-character "\u2573"'
Enter
Sleep 0.1
Type@0 ':set-background-pattern-2'
Enter
Sleep 0.1
Type@0 ':set-color-scheme-custom'
Enter
Sleep 0.1

# Open the command bar and start typing a command
Alt+:
Type 'a'
Sleep 0.1
Tab
Tab
Tab
Tab
Sleep 2

Screenshot gallery.v3.command-bar.png
