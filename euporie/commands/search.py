"""Defines commands related to searching."""

# Search

# register("abort-search")(abort_search)
# register("accept-search")(accept_search)
# register("start-reverse-incremental-search")(start_reverse_incremental_search)
# register("start-forward-incremental-search")(start_forward_incremental_search)
# register("reverse-incremental-search")(reverse_incremental_search)
# register("forward-incremental-search")(forward_incremental_search)
# register("accept-search-and-accept-input")(accept_search_and_accept_input)

"""

        @kb.add("c-f", group="Edit Mode", desc="Find")
        def find(event: "KeyPressEvent") -> "None":
            start_search(self.control)

        @kb.add("c-g", group="Edit Mode", desc="Find Next")
        def find_next(event: "KeyPressEvent") -> "None":
            search_state = get_app().current_search_state
            cursor_position = event.current_buffer.get_search_position(
                search_state, include_current_position=False
            )
            event.current_buffer.cursor_position = cursor_position
"""
