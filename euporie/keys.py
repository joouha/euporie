"""Defines KeyBindings wrapper which keeps track of key binding descriptions."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from aenum import extend_enum  # type: ignore
from prompt_toolkit.formatted_text import to_formatted_text
from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

if TYPE_CHECKING:
    from typing import Any, Callable, Optional, Union

    from prompt_toolkit.formatted_text import FormattedText
    from prompt_toolkit.key_binding.key_bindings import T

__all__ = ["KeyBindingsInfo"]

# Register additional keys
extend_enum(Keys, "ControlEnter", "c-enter")
extend_enum(Keys, "ControlShiftEnter", "c-s-enter")
extend_enum(Keys, "ShiftEnter", "s-enter")

# Assign escape sequences to new keys
ANSI_SEQUENCES["\x1b[27;5;13~"] = Keys.ControlEnter  # type: ignore
ANSI_SEQUENCES["\x1b[13;5u"] = Keys.ControlEnter  # type: ignore

ANSI_SEQUENCES["\x1b[27;2;13~"] = Keys.ShiftEnter  # type: ignore
ANSI_SEQUENCES["\x1b[13;2u"] = Keys.ShiftEnter  # type: ignore

ANSI_SEQUENCES["\x1b[27;6;13~"] = Keys.ControlShiftEnter  # type: ignore
ANSI_SEQUENCES["\x1b[13;6u"] = Keys.ControlShiftEnter  # type: ignore


class KeyBindingsInfo(KeyBindings):
    """Wraps `prompt_toolkit.key_binding.KeyBinding` recording helpful deatils.

    Each key binding can be given a group and a description, which can be used to
    display a help message about which key bindings are available to the user.
    """

    details: "dict[str, dict[str, dict[tuple[Union[Keys, str]], None]]]" = {}

    def add(
        self,
        *keys: "Union[Keys, str]",
        key_str: "Optional[tuple[str]]" = None,
        group: "str" = "None",
        desc: "Optional[str]" = None,
        **kwargs: "Any",
    ) -> "Callable[[T], T]":
        """Decorator for adding a key bindings.

        As per `prompt_toolkit.key_binding.KeyBinding`, with additional arguments.

        Args:
            *keys: Keys to pass to `prompt_toolkit.key_binding.KeyBinding.add`.
            key_str: A string which can be user to over-ride the bound key sequence in
                the binding's description.
            group: The name of the group to which this key binding belongs.
            desc: A description of what this key-binding does.
            **kwargs: Key word arguments to pass to
                `prompt_toolkit.key_binding.KeyBinding.add`.

        Returns:
            A decorator function.

        """
        if desc is not None:
            key = cast("tuple[Union[Keys, str]]", key_str or keys)
            self.details.setdefault(group, {}).setdefault(desc, {})[key] = None
        return super().add(*keys, **kwargs)

    @classmethod
    def to_formatted_text(cls) -> "FormattedText":
        """Format the current key binding descriptions as formatted text.

        Returns:
            Formatted text giving a description of the key-bindings in each group.

        """
        key_details = {
            group: {
                " / ".join(
                    [
                        " ".join(
                            (
                                part.replace("c-", "ctrl-").replace("s-", "shift-")
                                for part in key
                            )
                        )
                        for key in keys
                    ]
                ): desc
                for desc, keys in info.items()
            }
            for group, info in cls.details.items()
        }
        max_key_len = (
            max([len(key) for group in key_details.values() for key in group]) + 1
        )

        fragment_list: "list[Union[tuple[str, str], tuple[str, str, Callable]]]" = []
        for group, item in key_details.items():
            fragment_list.append(("", " " * (max(0, max_key_len - len(group)))))
            fragment_list.append(("bold underline", f"{group}\n"))
            for key, desc in item.items():
                fragment_list.append(("bold", key.rjust(max_key_len)))
                fragment_list.append(("", f"  {desc}"))
                fragment_list.append(("", "\n"))
            fragment_list.append(("", "\n"))
        # Remove two newlines at the end
        fragment_list.pop()
        fragment_list.pop()

        return to_formatted_text(fragment_list)
