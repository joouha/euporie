"""Buffer processors."""

from typing import TYPE_CHECKING

from prompt_toolkit.layout.processors import AppendAutoSuggestion, Transformation

if TYPE_CHECKING:
    # from typing import Callable

    from prompt_toolkit.layout.processors import TransformationInput


class AppendLineAutoSuggestion(AppendAutoSuggestion):
    """Append the auto suggestion to the current line of the input."""

    def apply_transformation(self, ti: "TransformationInput") -> "Transformation":
        """Insert fragments at the end of the current line."""
        if ti.lineno == ti.document.cursor_position_row:
            buffer = ti.buffer_control.buffer

            if buffer.suggestion and ti.document.is_cursor_at_the_end_of_line:
                suggestion = buffer.suggestion.text
            else:
                suggestion = ""
            return Transformation(fragments=ti.fragments + [(self.style, suggestion)])
        else:
            return Transformation(fragments=ti.fragments)


'''
class OverflowProcessor(Processor):
    """Indicate truncated lines."""

    def __init__(
        self,
        char: "str" = ">",
        style: str = "class:overflow-indicator",
    ) -> None:
        self.style = style
        self.char = char

    def apply_transformation(self, ti: TransformationInput) -> Transformation:

        width = transformation_input.width
        document = transformation_input.document

        fragments = ti.fragments
        # Walk through all the fragments.
        if fragments and fragment_list_to_text(fragments).startswith(" "):
            t = (self.style, self.get_char())
            fragments = explode_text_fragments(fragments)

            for i in range(len(fragments)):
                if fragments[i][1] == " ":
                    fragments[i] = t
                else:
                    break

        return Transformation(fragments)
'''
