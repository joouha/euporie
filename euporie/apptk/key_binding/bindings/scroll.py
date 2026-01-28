from euporie.apptk.commands import add_cmd
from euporie.apptk.key_binding.bindings.scroll import (
    scroll_backward,
    scroll_forward,
    scroll_half_page_down,
    scroll_half_page_up,
    scroll_one_line_down,
    scroll_one_line_up,
)

add_cmd()(scroll_forward)
add_cmd()(scroll_backward)
add_cmd()(scroll_half_page_up)
add_cmd()(scroll_half_page_down)
add_cmd()(scroll_one_line_up)
add_cmd()(scroll_one_line_down)
