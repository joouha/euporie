<h1 align="center">euporie</h1>

<img src="https://user-images.githubusercontent.com/12154190/117550683-79526700-b039-11eb-8a83-1828c6ee8125.png" alt="screenshot 1" width="45%" align="right" />

# About

Euporie is a text-based user interface for running and editing Jupyter notebooks.

# Install

Euporie is on pypi, so can be installed using `pip` or [`pipx`](https://pipxproject.github.io/pipx/):

```bash
# install inside a virtualenv
pip install euporie

# install globally
pipx install euporie
```

You may wish to install some optional python dependencies to render images and HTML tables (but [see below](#image-support)):

```bash
pip install euporie[html-mtable,images-timg]
```

# Screenshots

<p align="center">
<img src="https://user-images.githubusercontent.com/12154190/117550685-7a839400-b039-11eb-98ac-8adb9ea2cfc3.png" alt="screenshot 2" width="19%" />
<img src="https://user-images.githubusercontent.com/12154190/117550686-7a839400-b039-11eb-8c6f-65c3cedf2f25.png" alt="screenshot 3" width="19%" />
<img src="https://user-images.githubusercontent.com/12154190/117550687-7b1c2a80-b039-11eb-867b-d5e9d8671495.png" alt="screenshot 4" width="19%" />
<img src="https://user-images.githubusercontent.com/12154190/117550688-7bb4c100-b039-11eb-9419-a10c8c0f9b21.png" alt="screenshot 5" width="19%" />
<img src="https://user-images.githubusercontent.com/12154190/117550689-7bb4c100-b039-11eb-9d90-44df4c0e0f03.png" alt="screenshot 6" width="19%" />
</p>

# Features

- Execute notebooks in the terminal
- Autocompletion in code cells
- Rich output support, including:
  - Markdown
  - Tables
  - Images
- Open multiple notebooks side-by-side
- Good performance with large notebook files

## Image Support

Euporie will attempt to render images in the best possible way it can. The following methods are supported:

- **Sixel**

  If supported by your terminal, euporie can show graphical images in cell outputs
  This requires one of the following:

  [`imagemagik`](https://www.imagemagick.org)
  [`timg`](https://github.com/adzierzanowski/timg)
  [`teimpy`](https://github.com/ar90n/teimpy)

- **Kitty's terminal image protocol**

  If your terminal supports [kitty's terminal graphics protocol](https://sw.kovidgoyal.net/kitty/graphics-protocol.html), euporie will use it to render images

- **Ansi art**

  This requires one of the following:

  [`timg`](https://github.com/hzeller/timg)
  [`catimg`](https://github.com/posva/catimg)
  [`icat`](https://github.com/atextor/icat)
  [`timg`](https://github.com/adzierzanowski/timg)
  [`tiv`](https://github.com/radare/tiv)
  [`viu`](https://github.com/atanunq/viu)
  [`img2unicode`](https://github.com/matrach/img2unicode)
  [`jp2a`](https://csl.name/jp2a/)
  [`img2txt`](http://caca.zoy.org/wiki/libcaca)

The kitty & sixel image rendering methods will fall back to ansi art images when rendering images in partially obscured cells, to prevent clipped images destroying the user interface.

For SVG support, [`cairosvg`](https://cairosvg.org/) or [`imagemagik`](https://www.imagemagick.org) are required.

## HTML Support

Euporie will attempt to render HTML outputs. This requires one of the following:

[`w3m`](http://w3m.sourceforge.net/)
[`elinks`](http://elinks.or.cz/)
[`lynx`](https://lynx.browser.org/)
[`links`](http://links.twibright.com/)
[`mtable`](https://github.com/liuyug/mtable)

_Note: only HTML tables will be displayed if `mtable` is used_

If none of these commands are found in your `$PATH`, the plain text representation will be used.

# Usage

```
usage: euporie [-h] [--verion] [--dump | --no-dump] [--dump-file [Path]]
               [--page | --no-page] [--key-map {emacs,vi}]
               [--run-after-external-edit bool] [--max-notebook-width int]
               [--background-pattern {0,1,2,3,4}] [--background-character str]
               [--line-numbers | --no-line-numbers] [--syntax-theme str]
               [Path ...]

positional arguments:
  Path                  List of file names to open

optional arguments:
  -h, --help            show this help message and exit
  --verion, -V          show program's version number and exit
  --dump, --no-dump     Output formatted file to display or file
  --dump-file [Path]    Output path when dumping file
  --page, --no-page     Pass output to pager
  --key-map {emacs,vi}  Key-binding mode for text editing
  --run-after-external-edit bool
                        Run cells after editing externally
  --max-notebook-width int
                        Maximum width of notebooks
  --background-pattern {0,1,2,3,4}
                        The background pattern to use
  --background-character str
                        Character for background pattern
  --line-numbers, --no-line-numbers
                        Show or hide line numbers
  --syntax-theme str    Syntax higlighting theme
```

# Key Bindings

|                                                                             Key Binding | Command                      |
| ---------------------------------------------------------------------------------------:|:---------------------------- |
|                                                                         **Application** |                              |
|                                                 <kbd><kbd>Ctrl</kbd>+<kbd>n</kbd></kbd> | Create a new notebook file   |
|                                                 <kbd><kbd>Ctrl</kbd>+<kbd>o</kbd></kbd> | Open file                    |
|                                                 <kbd><kbd>Ctrl</kbd>+<kbd>w</kbd></kbd> | Close the current file       |
|                                                 <kbd><kbd>Ctrl</kbd>+<kbd>q</kbd></kbd> | Quit euporie                 |
|                                                                          **Navigation** |                              |
|                                                                          <kbd>Tab</kbd> | Focus next element           |
|                                              <kbd><kbd>Shift</kbd>+<kbd>Tab</kbd></kbd> | Focus previous element       |
|                                                                            <kbd>[</kbd> | Scroll up                    |
|                                                                            <kbd>]</kbd> | Scroll down                  |
|                              <kbd><kbd>Ctrl</kbd>+<kbd>Up</kbd></kbd> / <kbd>Home</kbd> | Go to first cell             |
|                                                                       <kbd>Pageup</kbd> | Go up 5 cells                |
|                                                            <kbd>Up</kbd> / <kbd>k</kbd> | Go up one cell               |
|                                                          <kbd>Down</kbd> / <kbd>j</kbd> | Go down one cell             |
|                                                                     <kbd>Pagedown</kbd> | Go down 5 cells              |
|                             <kbd><kbd>Ctrl</kbd>+<kbd>Down</kbd></kbd> / <kbd>End</kbd> | Go to last cell              |
|                                                                            **Notebook** |                              |
|                                                                            <kbd>e</kbd> | Edit cell in $EDITOR         |
|                                                                        <kbd>Enter</kbd> | Enter cell edit mode         |
|                                                                       <kbd>Escape</kbd> | Exit cell edit mode \*       |
|                                                                <kbd>Escape Escape</kbd> | Exit cell edit mode quickly  |
|   <kbd><kbd>Ctrl</kbd>+<kbd>Enter</kbd></kbd> / <kbd><kbd>Ctrl</kbd>+<kbd>e</kbd></kbd> | Run cell\*                   |
|  <kbd><kbd>Shift</kbd>+<kbd>Enter</kbd></kbd> / <kbd><kbd>Ctrl</kbd>+<kbd>r</kbd></kbd> | Run then select next cell\*\*|
|                                                                           **Edit Mode** |                              |
|                                                 <kbd><kbd>Ctrl</kbd>+<kbd>f</kbd></kbd> | Find                         |
|                                                 <kbd><kbd>Ctrl</kbd>+<kbd>g</kbd></kbd> | Find Next                    |
|                                                 <kbd><kbd>Ctrl</kbd>+<kbd>z</kbd></kbd> | Undo                         |
|                                                 <kbd><kbd>Ctrl</kbd>+<kbd>d</kbd></kbd> | Duplicate line               |
|                                                                          <kbd>Tab</kbd> | Indent                       |
|                                              <kbd><kbd>Shift</kbd>+<kbd>Tab</kbd></kbd> | Unindent                     |
|                                                 <kbd><kbd>Ctrl</kbd>+<kbd>c</kbd></kbd> | Copy                         |
|                                                 <kbd><kbd>Ctrl</kbd>+<kbd>x</kbd></kbd> | Cut                          |
|                                                 <kbd><kbd>Ctrl</kbd>+<kbd>v</kbd></kbd> | Paste                        |

> \* There is a slight delay detecting an escape key-event. To exit edit mode quickly, double-press the escape key.
>
> \*\* <kbd><kbd>Shift</kbd>+<kbd>Enter</kbd></kbd> and <kbd><kbd>Ctrl</kbd>+<kbd>Enter</kbd></kbd> require your terminal to support CSI-u mode. If your terminal does not support this, it may be possible to work around this by remapping the keys in your terminal emulator - see below).

When in edit mode, emacs style key-bindings apply by default.

## Key Remapping

By default, VT100 terminal emulators do not distinguish between <kbd>Enter</kbd>, <kbd><kbd>Ctrl</kbd>+<kbd>Enter</kbd></kbd> & <kbd><kbd>Shift</kbd>+<kbd>Enter</kbd></kbd>. In order to work around this, it is possible to re-map these key bindings so they produce the escape code of another key. To replicate the `Ctrl + Enter` & `Shift + Enter` of Jupyter, you will need to remap the following shortcuts in your terminal:

|                              Key Combination | Output                                    |
| -------------------------------------------- | ----------------------------------------- |
| <kbd><kbd>Ctrl</kbd>+<kbd>Enter</kbd></kbd>  | <kbd><kbd>Ctrl</kbd>+<kbd>F20</kbd></kbd> |
| <kbd><kbd>Shift</kbd>+<kbd>Enter</kbd></kbd> | <kbd>F21</kbd>                            |

### xterm

Add the following to your `~/.Xresources`

```
*.vt100.translations: #override \n\
    Ctrl <Key>Return: string("\033\[19;6~") \n\
    Shift <Key>Return: string("\033\[20;2~") \n\
```

### konsole

In the menu, navigate to:

`Settings` -> `Edit Current Profile` -> `Keyboard` -> `Edit`

Change the existing entry for `Return+Shift` to `Return+Shift+Ctrl` (or whatever you prefer), then add the following entries:

| Key combination | Output      |
| --------------- | ----------- |
| `Return+Ctrl`   | `\E\[19;6~` |
| `Return+Shift`  | `\E\[20;2~` |

# Roadmap

- Add ability to dump formatted notebooks
- Add command line argument parsing
- Render outputs asynchronously in a separate thread
- Upstream markdown tables in `rich`
- Cell attachments
- LaTeX
- Widgets

# Related projects

- https://github.com/davidbrochart/nbterm

  An alternative effort sponsored by QuantStack

- https://github.com/chentau/nbtui

  A cli Jupyter notebook viewer with support for kitty's terminal graphics protocol

- https://github.com/mosiman/jupytui

  A cli Jupyter notebook viewer

- https://kracekumar.com/post/jut/

  Another cli Jupyter notebook viewer
