# euporie

<img src="https://user-images.githubusercontent.com/12154190/117550683-79526700-b039-11eb-8a83-1828c6ee8125.png" alt="screenshot 1" width="45%" align="right" />

# About

Euporie is a text-based user interface for running and editing Jupyter notebooks.

# Install

Euporie is on pypi, so can be installed using pip:

```bash
pip install euporie
```

If you are using Windows, you may wish to install some optional python dependencies to render images and HTML tables:

```bash
pip install euporie[tables,images]
```

# Screenshots

<p align="center">
<img src="https://user-images.githubusercontent.com/12154190/117550685-7a839400-b039-11eb-98ac-8adb9ea2cfc3.png" alt="screenshot 2" width="19%" />
<img src="https://user-images.githubusercontent.com/12154190/117550686-7a839400-b039-11eb-8c6f-65c3cedf2f25.png" alt="screenshot 3" width="19%" />
<img src="https://user-images.githubusercontent.com/12154190/117550687-7b1c2a80-b039-11eb-867b-d5e9d8671495.png" alt="screenshot 4" width="19%" />
<img src="https://user-images.githubusercontent.com/12154190/117550688-7bb4c100-b039-11eb-9419-a10c8c0f9b21.png" alt="screenshot 5" width="19%" />
<img src="https://user-images.githubusercontent.com/12154190/117550689-7bb4c100-b039-11eb-9d90-44df4c0e0f03.png" alt="screenshot 6" width="19%" />
</p>

# Usage

To open a notebook file, pass the file name as a command line parameter:

```bash
euporie ~/my-notebook.ipynb
```

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

## Key Bindings

| Command                         | Key Binding                               |
| ------------------------------- | ----------------------------------------- |
| Quit                            | `Ctrl + q`                                |
| Open notebook                   | `Ctrl + o`                                |
| New notebook                    | `Ctrl + n`                                |
| Close notebook                  | `Ctrl + w`                                |
| Select next cell                | `Up`, `k`                                 |
| Select previous cell            | `Down`, `j`                               |
| Page up (move up 5 cells)       | `Pgup`                                    |
| Page down (move down 5 cells)   | `PgDown`                                  |
| Scroll up                       | `[`                                       |
| Scroll down                     | `]`                                       |
| Enter edit mode                 | `Enter`                                   |
| Exit edit mode                  | `Esc`\*, `Esc, Esc`                       |
| Edit cell in `$EDITOR`          | `e`                                       |
| Run cell                        | `Ctrl + Enter`\*\*, `Ctrl + Space`, `F20` |
| Run cell and select next cell   | `Shift + Enter`\*\*, `F21`                |
| Insert cell above selected cell | `a`                                       |
| Insert cell below selected cell | `b`                                       |
| Toggle line numbers             | `l`                                       |
| Copy cell                       | `c`                                       |
| Cut cell                        | `x`                                       |
| Paste cell                      | `v`                                       |
| Delete cell                     | `dd`                                      |

> \* There is a slight delay detecting an escape key-event. To exit edit mode quickly, double-press the escape key.
>
> \*\* These entries require key remapping in your terminal in order to work - see below).

When in edit mode, emacs style key-bindings apply.

### Key Remapping

By default, VT100 terminal emulators do not distinguish between `Enter`, `Ctrl + Enter` & `Shift + Enter`. In order to work around this, it is possible to re-map these key bindings so they produce the escape code of another key. To replicate the `Ctrl + Enter` & `Shift + Enter` of Jupyter, you will need to remap the following shortcuts in your terminal:

| Key Combination | Output       |
| --------------- | ------------ |
| `Ctrl + Enter`  | `Ctrl + F20` |
| `Shift + Enter` | `F21`        |

#### xterm

Add the following to your `~/.Xresources`

```
*.vt100.translations: #override \n\
    Ctrl <Key>Return: string("\033\[19;6~") \n\
    Shift <Key>Return: string("\033\[20;2~") \n\
```

#### konsole

In the menu, navigate to:

`Settings` -> `Edit Current Profile` -> `Keyboard` -> `Edit`

Change the existing entry for `Return+Shift` to `Return+Shift+Ctrl` (or whatever you prefer), then add the following entries:

| Key combination | Output      |
| --------------- | ----------- |
| `Return+Ctrl`   | `\E\[19;6~` |
| `Return+Shift`  | `\E\[20;2~` |

# Roadmap

- Add a configuration file to expose configurable settings
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
