Set Cols 160
Set Rows 40

Hide
Source common.setup.tape

# Launch with a new notebook
Type@0 "euporie notebook --show-side-bar"
Enter
Sleep 2s
Ctrl+N
Sleep 1s

Alt+:
Type@0 'set-color-scheme-black'
Enter
Alt+:
Type@0 'set-side-bar-panel-index None'
Enter
Type w


# Create a markdown cell containing a mermaid diagram

Type m
Enter


Type@0 '# Mermaid Diagrams in Markdown'
Enter
Enter
Type@0 '<style>td, table {border-width: 0px; text-align: center}</style>'
Enter
Type@0 '<table style="width:100%"><tr><td>'
Enter
Enter
Type@0 '```mermaid'
Enter
Type@0 'graph TD'
Enter
Type@0 'A[Start] --> B{Is it working?}'
Enter
Type@0 'B -->|Yes| C[Great!]'
Enter
Type@0 'B -->|No| D[Debug]'
Enter
Type@0 'D --> B'
Enter
Type@0 '```'
Enter
Enter
Type@0 '</td>'
Enter
Type@0 '<td>'
Enter
Enter
Type@0 '```mermaid'
Enter
Type@0 'sequenceDiagram'
Enter
Type@0 'Alice->>Bob: Hello!'
Enter
Type@0 'Bob->>Charlie: Forward message'
Enter
Type@0 'Charlie-->>Alice: Got it!'
Enter
Type@0 '```'
Enter
Enter
Type@0 '</td>'
Enter
Type@0 '</tr><tr>'
Enter
Type@0 '<td>'
Enter
Enter
Type@0 '```mermaid'
Enter
Type@0 'graph LR'
Enter
Type@0 'A --> B & C'
Enter
Type@0 'B --> C & D'
Enter
Type@0 'D --> C'
Enter
Type@0 '```'
Enter
Enter
Type@0 '</td>'
Enter
Enter
Type@0 '<td>'
Enter
Enter
Type@0 '```mermaid'
Enter
Type@0 'graph LR'
Enter
Type@0 'classDef example1 color:#ff0000'
Enter
Type@0 'classDef example2 color:#00ff00'
Enter
Type@0 'classDef example3 color:#0000ff'
Enter
Type@0 'test1:::example1 --> test2'
Enter
Type@0 'test2:::example2 --> test3:::example3'
Enter
Type@0 '```'
Enter
Enter
Type@0 '</td>'
Enter
Type@0 '</tr></table>'

Ctrl+E
Sleep 30
Home
Sleep 2

Screenshot gallery.v3.mermaid-diagrams.png
Sleep 2
