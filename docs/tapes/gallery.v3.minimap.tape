Set Cols 160
Set Rows 40

Hide
Source common.setup.tape

# Launch with a new notebook
Type@0 "euporie notebook --max-notebook-width=90"
Enter
Sleep 2s
Ctrl+N
Wait /ipykernel/
Wait /○/
Sleep 500ms

# Open the minimap via the command bar
Alt+:
Type@0 'set-show-side-bar True'
Enter
Alt+:
Type@0 'set-side-bar-panel-index 2'
Enter
Alt+:
Type@0 'set-side-bar-width 40'
Enter
# Zoom the minimap in
Alt+:
Type@0 'zoom-minimap-in 15'
Enter
Sleep 500ms


# Add enough cells to fill the notebook and show the minimap
Enter
Type@0 'import numpy as np'
Enter
Type@0 'import math'
Enter
Type@0 'from itertools import chain, product'
Enter
Type@0 'from collections import Counter, defaultdict'
Enter
Enter
Type@0 'def fibonacci(n):'
Enter
Type@0 'a, b = 0, 1'
Enter
Type@0 'for _ in range(n):'
Enter
Type@0 'a, b = b, a + b'
Enter
Backspace
Type@0 'return a'
Ctrl+R
Enter
Type@0 'values = [fibonacci(i) for i in range(20)]'
Enter
Type@0 'doubled = [v * 2 for v in values]'
Enter
Type@0 'summed = sum(values) + sum(doubled)'
Enter
Type@0 'print(values, doubled, summed)'
Ctrl+R
Enter
Type@0 'matrix = np.arange(100).reshape(10, 10)'
Enter
Type@0 'transposed = matrix.T'
Enter
Type@0 'diagonal = np.diag(matrix)'
Enter
Type@0 'product_matrix = matrix @ transposed'
Ctrl+R
Enter
Type@0 'print("Matrix:")'
Enter
Type@0 'print(matrix)'
Enter
Type@0 'print("Diagonal:")'
Enter
Type@0 'print(diagonal)'
Ctrl+R
Enter
Type@0 'total = sum(values)'
Enter
Type@0 'average = total / len(values)'
Enter
Type@0 'maximum = max(values)'
Enter
Type@0 'minimum = min(values)'
Ctrl+R
Enter
Type@0 'print(f"Total: {total}")'
Enter
Type@0 'print(f"Average: {average}")'
Enter
Type@0 'print(f"Max: {maximum}")'
Enter
Type@0 'print(f"Min: {minimum}")'
Ctrl+R
Enter
Type@0 'squares = {i: i ** 2 for i in range(10)}'
Enter
Type@0 'cubes = {i: i ** 3 for i in range(10)}'
Enter
Type@0 'roots = {i: math.sqrt(i) for i in range(10)}'
Enter
Type@0 'combined = {**squares, **cubes}'
Ctrl+R
Enter
Type@0 'print("Squares:", squares)'
Enter
Type@0 'print("Cubes:", cubes)'
Enter
Type@0 'print("Roots:", roots)'
Enter
Type@0 'print("Combined:", combined)'
Ctrl+R
Enter
Type@0 'names = ["alice", "bob", "charlie", "dave"]'
Enter
Type@0 'ages = [30, 25, 35, 40]'
Enter
Type@0 'cities = ["london", "paris", "berlin", "madrid"]'
Enter
Type@0 'occupations = ["engineer", "artist", "doctor", "teacher"]'
Ctrl+R
Enter
Type@0 'upper = [name.upper() for name in names]'
Enter
Type@0 'lower = [city.lower() for city in cities]'
Enter
Type@0 'titles = [job.title() for job in occupations]'
Enter
Type@0 'lengths = [len(name) for name in names]'
Ctrl+R
Enter
Type@0 'print("Upper:", upper)'
Enter
Type@0 'print("Lower:", lower)'
Enter
Type@0 'print("Titles:", titles)'
Enter
Type@0 'print("Lengths:", lengths)'
Ctrl+R
Enter
Type@0 'x = 1'
Enter
Type@0 'y = 2'
Enter
Type@0 'z = 3'
Enter
Type@0 'w = x + y + z'
Ctrl+R
Enter
Wait /○/
Type@0 'long_variable_name = "This is a much longer line with a descriptive string value assigned to it for demonstration"'
Enter
Type@0 'another_long_name = "Yet another long descriptive string used to fill out the line for visual demonstration purposes"'
Enter
Type@0 'third_long_name = "A third example of a long variable assignment with plenty of characters to fill the line up"'
Enter
Type@0 'combined_length = len(long_variable_name) + len(another_long_name) + len(third_long_name)'
Ctrl+R
Wait /○/
Enter
Type@0 'pairs = list(zip(names, values[:len(names)]))'
Enter
Type@0 'triples = list(zip(names, ages, cities))'
Enter
Type@0 'indexed = list(enumerate(names))'
Enter
Type@0 'reversed_pairs = pairs[::-1]'
Ctrl+R
Enter
Type@0 'for name, value in pairs:'
Enter
Type@0 'print(f"{name}: {value}")'
Enter
Backspace
Type@0 'for name, age, city in triples:'
Enter
Type@0 'print(f"{name} ({age}) from {city}")'
Ctrl+R
Wait /○/
Enter
Type@0 'a = 42'
Enter
Type@0 'b = 100'
Enter
Type@0 'c = a * b'
Enter
Type@0 'd = c // (a + b)'
Ctrl+R
Wait /○/
Enter
Type@0 'result = sum(x ** 2 for x in range(1, 101) if x % 2 == 0) + sum(y ** 3 for y in range(1, 51) if y % 3 == 0)'
Enter
Type@0 'even_squares = [x ** 2 for x in range(1, 101) if x % 2 == 0]'
Enter
Type@0 'odd_cubes = [y ** 3 for y in range(1, 51) if y % 2 == 1]'
Enter
Type@0 'grand_total = sum(even_squares) + sum(odd_cubes)'
Ctrl+R
Wait /○/
Enter
Type@0 'print(result)'
Enter
Type@0 'print(grand_total)'
Enter
Type@0 'print(len(even_squares))'
Enter
Type@0 'print(len(odd_cubes))'
Ctrl+E
Wait /○/
Sleep 2
Escape
Escape
Sleep 0.1
Pageup
Down
Sleep 0.1
Enter
Sleep 0.1
Sleep 1

Screenshot gallery.v3.minimap.png
