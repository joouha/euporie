##########
ipywidgets
##########

`ipywidgets <https://ipywidgets.readthedocs.io/>`_ are interactive HTML controls that run in a Jupyter notebook and communicate with the kernel via the Jupyter messaging protocol. Euporie reimplements many of the standard widgets in plain text so they can be used in the terminal.

***********
Installing
***********

Inside whatever environment your kernel runs in, install :py:mod:`ipywidgets`:

.. code-block:: console

   $ pip install ipywidgets

You don't need to install anything in euporie's environment - widgets are rendered by euporie based on the messages the kernel emits.

*************
Using widgets
*************

Use widgets exactly as you would in JupyterLab:

.. code-block:: python

   from ipywidgets import IntSlider, interact

   @interact(x=IntSlider(min=0, max=100, value=50))
   def show(x):
       print(f"x squared is {x*x}")

Run the cell. A slider appears in the cell output; use the arrow keys
(:kbd:`Left`/:kbd:`Right`) or click and drag with the mouse to change its
value. The Python callback re-runs whenever the slider changes.

*****************
Supported widgets
*****************

Most of the controls in the standard :py:mod:`ipywidgets` library work in euporie:

* :py:class:`~ipywidgets.widgets.widget_int.IntSlider`, :py:class:`~ipywidgets.widgets.widget_float.FloatSlider`,
  :py:class:`~ipywidgets.widgets.widget_int.IntRangeSlider`, :py:class:`~ipywidgets.widgets.widget_float.FloatRangeSlider`
* :py:class:`~ipywidgets.widgets.widget_int.IntText`, :py:class:`~ipywidgets.widgets.widget_float.FloatText`,
  :py:class:`~ipywidgets.widgets.widget_string.Text`, :py:class:`~ipywidgets.widgets.widget_string.Textarea`,
  :py:class:`~ipywidgets.widgets.widget_string.Password`
* :py:class:`~ipywidgets.widgets.widget_bool.Checkbox`, :py:class:`~ipywidgets.widgets.widget_bool.Valid`,
  :py:class:`~ipywidgets.widgets.widget_bool.ToggleButton`, :py:class:`~ipywidgets.widgets.widget_button.Button`
* :py:class:`~ipywidgets.widgets.widget_selection.Dropdown`, :py:class:`~ipywidgets.widgets.widget_selection.Select`,
  :py:class:`~ipywidgets.widgets.widget_selection.SelectMultiple`, :py:class:`~ipywidgets.widgets.widget_selection.RadioButtons`,
  :py:class:`~ipywidgets.widgets.widget_selection.ToggleButtons`
* :py:class:`~ipywidgets.widgets.widget_box.HBox`, :py:class:`~ipywidgets.widgets.widget_box.VBox`,
  :py:class:`~ipywidgets.widgets.widget_box.GridBox`, :py:class:`~ipywidgets.widgets.widget_selectioncontainer.Tab`,
  :py:class:`~ipywidgets.widgets.widget_selectioncontainer.Accordion`
* :py:class:`~ipywidgets.widgets.widget_output.Output`, :py:class:`~ipywidgets.widgets.widget_string.HTML`,
  :py:class:`~ipywidgets.widgets.widget_media.Image`, :py:class:`~ipywidgets.widgets.widget_string.Label`
* :py:class:`~ipywidgets.widgets.widget_int.Play`, :py:class:`~ipywidgets.widgets.widget_date.DatePicker`,
  :py:class:`~ipywidgets.widgets.widget_color.ColorPicker`, :py:class:`~ipywidgets.widgets.widget_upload.FileUpload`

Custom widgets that follow the standard widget protocol may also work, but will fall back to a textual placeholder if euporie has no specific renderer for them.

******
ipympl
******

`ipympl <https://matplotlib.org/ipympl/>`_ provides an interactive matplotlib backend built on :py:mod:`ipywidgets`, and is supported by euporie.

Install ``ipympl`` inside your kernel's environment:

.. code-block:: console

   $ pip install ipympl

Then activate the backend in a cell using the ``%matplotlib`` magic:

.. code-block:: python

   %matplotlib ipympl
   import matplotlib.pyplot as plt
   import numpy as np

   fig, ax = plt.subplots()

   x = np.linspace(0, 2 * np.pi, 100)
   y = np.sin(3 * x)
   ax.plot(x, y)

You can also use ``%matplotlib widget``, which has the same effect. The resulting figure is rendered as a widget in the cell output, allowing interactive panning and zooming from within the terminal.

***********
Limitations
***********

* JavaScript-based widgets (e.g. WebGL plots, leaflet maps) cannot run in the terminal. They will display a textual placeholder.
* Widgets that depend on browser DOM events (drag-and-drop, scroll-based triggers) are typically inert.
* Layout properties like exact pixel widths are honoured approximately - the cell terminal grid is used as the layout unit.

***********
See also
***********

* :doc:`terminal_graphics` - how images embedded in widgets are rendered
* :doc:`kernels` - selecting an environment that has :py:mod`ipywidgets` installed
