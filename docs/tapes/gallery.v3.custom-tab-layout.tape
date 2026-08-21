Set Cols 160
Set Rows 40

Hide
Source common.setup.tape

# Launch with multiple notebooks to demonstrate a custom tab layout
Type@0 "euporie notebook --no-wrap-cell-outputs"
Enter
Sleep 2s

# First notebook: colorful matplotlib sine wave plot
Ctrl+N
Sleep 1s
Enter
Sleep 0.1
Type@0 'import numpy as np, matplotlib.pyplot as plt'
Enter
Type@0 'x = np.linspace(0, 4 * np.pi, 200)'
Enter
Type@0 'fig, ax = plt.subplots(figsize=(6, 3))'
Enter
Type@0 'for i, c in enumerate(["#e63946", "#f4a261", "#2a9d8f", "#264653"]):'
Enter
Type@0 'ax.plot(x, np.sin(x + i * np.pi / 4), color=c, linewidth=2)'
Sleep 0.1
Ctrl+R
Sleep 0.1

# Second cell: add a colorbar heatmap
Enter
Sleep 0.1
Type@0 'data = np.sin(x[:, None]) * np.cos(x[None, :])'
Enter
Type@0 'fig, ax = plt.subplots(figsize=(6, 2))'
Enter
Type@0 'im = ax.imshow(data, cmap="magma", aspect="auto")'
Enter
Type@0 'fig.colorbar(im, ax=ax);'
Ctrl+E
Sleep 0.1
Home
Up
Sleep 1s

# Second notebook: LaTeX math equations
Ctrl+N
Sleep 1s
Type m
Enter
Sleep 0.1
Type@0 '## Famous equations'
Enter
Enter
Type@0 '$$e^{i\pi} + 1 = 0$$ '
Type@0 '$$\int_{-\infty}^{\infty} e^{-x^2}\,dx = \sqrt{\pi}$$ '
Type@0 '$$\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}$$ '
Type@0 '$$x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$$ '
Sleep 0.1
Sleep 0.1
Ctrl+E
Sleep 1s

# Third notebook: TBC
Ctrl+N
Sleep 1s
Enter
Type@0 'import ipywidgets as w'
Enter
Type@0 'w.VBox([w.Button(description="Button", icon="mouse-pointer"), w.Select(options=["Apples", "Oranges", "Bananas", "Pears", "Cherries", "Apricots", "Peaches"], rows=3), w.FloatProgress(value=25.1, bar_style="danger", description="Progress Bar")])'
Home
Sleep 0.1
Ctrl+E
Sleep 1s

# Fourth notebook: styled pandas DataFrame with gradient background
Ctrl+N
Wait /○/
Enter
Sleep 0.1
Type@0 'import numpy as np'
Enter
Type@0 'import pandas as pd'
Enter
Type@0 'df = pd.DataFrame(np.random.default_rng(42).normal(size=(8, 5)), columns=list("ABCDE"))'
Enter
Type@0 'df.style.background_gradient(cmap="viridis").format("{:.2f}")'
Home
Sleep 0.1
Ctrl+E
Sleep 1s

# Tile the open tabs
Alt+:
Sleep 0.5
Type@0 'tile-tabs'
Enter
Sleep 1

Home
Sleep 2

Screenshot gallery.v3.custom-tab-layout.png
