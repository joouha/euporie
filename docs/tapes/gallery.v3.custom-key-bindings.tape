Set Cols 160
Set Rows 40

Hide
Source common.setup.tape

Type@0 "cat >> ~/.config/euporie/config.toml <<'EOF'"
Enter
Enter
Type@0 '[notebook.key_bindings]'
Enter
Type@0 'run-input = ["c-x c-x c-x r"]'
Enter
Type@0 'clear-input = ["c-x c-c c-l i"]'
Enter
Type@0 'clear-screen = ["c-x escape c-l s"]'
Enter
Type@0 'previous-tab = ["c-x c-b left left"]'
Enter
Type@0 'show-command-palette = ["c-x c-x A-x p"]'
Enter
Type@0 'activate-command-bar = ["escape escape c-x b"]'
Enter
Type@0 'focus-next = ["c-x c-x c-n"]'
Enter
Type@0 'activate-command-bar-shell = ["escape escape c-x c-!"]'
Enter
Type@0 'quit = ["c-x c-x c-c c-q"]'
Enter
Type@0 'open-file = ["c-x c-x c-f"]'
Enter
Type@0 'close-tab = ["c-x c-x c-k"]'
Enter
Type@0 'next-tab = ["c-x c-b right right"]'
Enter
Type@0 'save-tab = ["c-x c-x c-s t"]'
Enter
Type@0 'focus-previous = ["c-x c-x c-p"]'
Enter
Type@0 'save-file = ["c-x c-x c-c c-s"]'
Enter
Type@0 'refresh-tab = ["c-x escape g g g"]'
Enter
Type@0 'new-notebook = ["c-x c-x c-c c-n b"]'
Enter
Type@0 'new-console = ["c-x c-x c-c c-n c"]'
Enter
Type@0 'new-terminal = ["c-x c-x c-c c-n t"]'
Enter
Type@0 'new-text-file = ["c-x c-x c-c c-n f"]'
Enter
Type@0 'save-as = ["c-x c-x c-w a"]'
Enter
Type@0 'EOF'
Enter


# Launch with a new notebook
Type@0 "euporie notebook"
Enter
Sleep 2

# Open the key bindings configuration dialog via the command palette
Alt+H
Sleep 0.1
Down
Down
Sleep 0.1
Enter
Sleep 2
Alt+F
Sleep 10

Screenshot gallery.v3.custom-key-bindings.png
