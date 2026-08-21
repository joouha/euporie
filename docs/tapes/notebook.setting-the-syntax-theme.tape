Set Cols 80
Set Rows 20

Hide
Source common.setup.tape

# Launch with a new notebook
Type@0 "euporie notebook"
Enter
Sleep 2s
Ctrl+N
Sleep 2s
# Enter code into a cell
Enter
Type@0 'import numpy as np'
Enter
Type@0 'import pandas as pd'
Enter
Enter
Type@0 'def load_data() -> pd.DataFrame:'
Enter
Type@0 'x = np.arange(20_000)'
Enter
Type@0 'df = pd.DataFrame('
Enter
Type@0 '{'
Enter
Type@0 'col: np.random.beta(i + 1, 3, x.shape)'
Enter
Type@0 'for col, i in zip("abcd", [0, 2, 4, 8])'
Down
Type@0 ','
Enter
Type@0 'index=x,'
Down
Enter
Type@0 'return df'
Home
Home
Escape
Escape
Sleep 0.1
Show
Sleep 2

Alt+S
Sleep 0.5
Down
Sleep 0.5
Down
Sleep 0.5
Down
Sleep 0.5
Right
Sleep 0.5
Down
Down
Down
Down
Down
Down
Down
Down
Down
Down
Down
Sleep 1
Enter
Sleep 2

Type ':set-syntax-theme-monokai'
Enter
Sleep 2

Hide
Type@0 ':set-syntax-theme-coffee'
Enter
Show
Sleep 2

Hide
Type@0 ':set-syntax-theme-default'
Enter
Show
Sleep 2

Hide
Type@0 ':set-syntax-theme-emacs'
Enter
Show
Sleep 2

Hide
Type@0 ':set-syntax-theme-fruity'
Enter
Show
Sleep 2

Hide
Type@0 ':set-syntax-theme-gruvbox-dark'
Enter
Show
Sleep 2

Hide
Type@0 ':set-syntax-theme-inkpot'
Enter
Show
Sleep 2

Hide
Type@0 ':set-syntax-theme-lightbulb'
Enter
Show
Sleep 2

Hide
Type@0 ':set-syntax-theme-manni'
Enter
Show
Sleep 2

Hide
Type@0 ':set-syntax-theme-material'
Enter
Show
Sleep 2

Hide
Type@0 ':set-syntax-theme-euporie'
Enter
Show
Sleep 4



