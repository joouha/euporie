"""Interface for an output."""

from __future__ import annotations

from abc import ABCMeta

from prompt_toolkit.output.base import Output as PtkOutput

from euporie.apptk.data_structures import Size

__all__ = ["Output"]


class Output(PtkOutput, metaclass=ABCMeta):
    """Base class defining the output interface for a :class:`~prompt_toolkit.renderer.Renderer`.

    Actual implementations are
    :class:`~prompt_toolkit.output.vt100.Vt100_Output` and
    :class:`~prompt_toolkit.output.win32.Win32Output`.
    """

    def mplex_passthrough(self, cmd: str) -> str:
        """Wrap an escape sequence for terminal passthrough."""
        return cmd

    def get_pixel_size(self) -> Size:
        """Return terminal size in pixels."""
        size = self.get_size()
        return Size(size.x * 10, size.y * 20)

    def set_pixel_size(self, px: int, py: int) -> None:
        """Set terminal pixel dimensions."""

    @property
    def cell_pixel_size(self) -> Size:
        """Get the pixel size of a single terminal cell."""
        px, py = self.get_pixel_size()
        rows, cols = self.get_size()
        # If we can't get the pixel size, just guess wildly
        return Size(px // cols or 10, py // rows or 20)

    def enable_sgr_pixel(self) -> None:
        """Enable SGR-pixel mouse positioning."""

    def disable_sgr_pixel(self) -> None:
        """Disable SGR-pixel mouse positioning."""

    def enable_palette_dsr(self) -> None:
        """Enable device status reports for color palette updates."""

    def disable_palette_dsr(self) -> None:
        """Disable device status reports for color palette updates."""

    def enable_extended_keys(self) -> None:
        """Request extended keys."""

    def disable_extended_keys(self) -> None:
        """Disable extended keys."""

    def set_clipboard(self, text: str) -> None:
        """Set clipboard data using OSC-52."""

    def ask_for_clipboard(self) -> None:
        """Get clipboard contents using OSC-52."""

    def ask_for_colors(self) -> None:
        """Query terminal colors."""

    def ask_for_pixel_size(self) -> None:
        """Check the terminal's dimensions in pixels."""

    def ask_for_kitty_graphics_status(self) -> None:
        """Query terminal to check for kitty graphics support."""

    def ask_for_device_attributes(self) -> None:
        """Query terminal for device attributes."""

    def ask_for_iterm_graphics_status(self) -> None:
        """Query terminal for iTerm graphics support."""

    def ask_for_sgr_pixel_status(self) -> None:
        """Query terminal to check for Pixel SGR support."""

    def ask_for_csiu_status(self) -> None:
        """Query terminal to check for CSI-u support."""
