Set Cols 160
Set Rows 40

Hide
Source common.setup.tape

# Launch with a new notebook
Type@0 "euporie-notebook --show-side-bar"
Enter
Sleep 2s
Ctrl+N
Wait /ipykernel/
Sleep 500ms

Alt+:
Type@0 'set-side-bar-panel-index None'
Enter

# Produce some text output
Enter
Type@0 'from IPython.display import *'
Enter
Enter
Type@0 's = ["# Output title", "", *["1. " + " ".join( f"**{x}**" if i == j else x for j, x in enumerate(list("The quick brown fox jumps over the lazy dog".split())[:i+1]) ) for i in range(9) ], "", "---", "| A | B | C |", "|---|---|---|", "| 1 | 2 | 3 |", "| 4 | 5 | 6 |", "| 7 | 8 | 9 |"]'
Enter
Type@0 'display(Markdown("\n".join(s)))'
Home
Ctrl+E
Wait /○/
Sleep 1
Up

# Select text in the output by dragging with the mouse
Type@0 "[<0;853;190M"
Sleep 0.3
Type@0 "[<32;625;636M"
Sleep 1
Sleep 2

Screenshot gallery.v3.output-selection.png
