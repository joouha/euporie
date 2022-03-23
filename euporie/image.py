from euporie.convert.base import convert


def math(ft, width, block, **kwargs):
    result = []
    for (style, value) in ft:
        result.append(
            (
                style,
                convert(value, "latex", "ansi"),
            )
        )
    if block:
        result = align("center", result, width=width)
        result.append(("", "\n\n"))
    return result


def img(ft, width, attrs, block, left, border: "bool" = False, **kwargs):
    import urllib

    result = []

    src = attrs.get("src")
    # Try and load the image bytes
    # TODO - move image loading somewhere else
    if src and False:
        try:
            image_bytes = urllib.request.urlopen(src).read()
        except Exception:
            pass
        else:
            from prompt_toolkit.application.current import _current_app_session, get_app

            from euporie.app.tui import TuiApp
            from euporie.output.container import get_dims

            if not isinstance(get_app(), TuiApp):
                _current_app_session.get().app = TuiApp()

            # Display it graphically
            cols, aspect = get_dims(data=image_bytes, format_="png")
            result = list(
                to_formatted_text(
                    ANSI(
                        convert(
                            image_bytes,
                            "png",
                            "ansi",
                            cols=cols,
                            rows=int(cols * aspect),
                        )
                    )
                )
            )
            result = strip(result, char="\n")
            if border:
                result = add_border(
                    result,
                    width=cols + 4,
                    border=RoundBorder,
                    style="class:md.img.border",
                )
            result = indent(result, " " * left, skip_first=True)

    if not result:
        result = [("", "🖼️  "), *ft]
        result = apply_style(result, style="class:md.image.placeholder")
        result = [("class:md.img.border", "[ "), *result, ("class:md.img.border", " ]")]

    return result
