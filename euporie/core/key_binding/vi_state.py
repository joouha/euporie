"""Create a Vi state which defaults to navigation mode."""

from prompt_toolkit.key_binding.vi_state import InputMode
from prompt_toolkit.key_binding.vi_state import ViState as PtkViState


class ViState(PtkViState):
    """Mutable class to hold the state of the Vi navigation."""

    def __init__(self) -> "None":
        """Set initial mode to navigation."""
        super().__init__()
        #: The Vi mode we're currently in to.
        self.__input_mode = InputMode.NAVIGATION

    def reset(self) -> "None":
        """Reset state, go back to the given mode. NAVIGATION by default."""
        super().reset()
        # Go back to navigation mode.
        self.input_mode = InputMode.NAVIGATION
