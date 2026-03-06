"""Define the Setting class for configuration items."""

from __future__ import annotations

import argparse
from functools import cached_property
from typing import TYPE_CHECKING, Any

from apptk.filters.utils import to_filter

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from apptk.filters.base import FilterOrBool
    from apptk.widgets.menus import MenuItem

_SCHEMA_TYPES: dict[type | Callable, str] = {
    bool: "boolean",
    str: "string",
    int: "integer",
    float: "number",
}


class BooleanOptionalAction(argparse.Action):
    """Action for boolean flags with --no- prefix support."""

    def __init__(self, option_strings: list[str], *args: Any, **kwargs: Any) -> None:
        """Initiate the Action with --no- variants."""
        _option_strings = list(option_strings)
        for option_string in option_strings:
            if option_string.startswith("--"):
                _option_strings.append(f"--no-{option_string[2:]}")
        kwargs["nargs"] = 0
        super().__init__(_option_strings, *args, **kwargs)

    def format_usage(self) -> str:
        """Format the action string."""
        return " | ".join(self.option_strings)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        """Set the value based on whether --no- prefix was used."""
        if option_string in self.option_strings:
            assert isinstance(option_string, str)
            setattr(namespace, self.dest, not option_string.startswith("--no-"))


TYPE_ACTIONS: dict[Callable[[Any], Any], type[argparse.Action]] = {
    bool: BooleanOptionalAction
}


class Setting:
    """A single configuration item.

    Attributes:
        name: The setting name (used as key in config files and CLI flags).
        default: The default value.
        title: Human-readable title for menus.
        help: Short help text for CLI.
        description: Longer description for documentation.
        type: The type to cast values to.
        choices: Available choices (list, dict for aliases, or callable).
        flags: CLI flags (e.g., ["--color-scheme"]).
        hidden: Whether to hide from help output.
        hooks: Callbacks to run when value changes.
    """

    def __init__(
        self,
        name: str,
        apps: str | Sequence[str] = "*",
        default: Any = None,
        help_: str = "",
        description: str = "",
        type_: Callable[[Any], Any] | None = None,
        validate: Callable[[Any], Any] | None = None,
        title: str | None = None,
        choices: list[Any] | dict | Callable[[], list[Any] | dict] | None = None,
        action: argparse.Action | str | None = None,
        flags: list[str] | None = None,
        schema: dict[str, Any] | None = None,
        nargs: str | int | None = None,
        nullable: bool | None = None,
        hidden: FilterOrBool = False,
        hooks: list[Callable[[Setting], None]] | None = None,
        # Accept but ignore legacy 'group' parameter for compatibility
        group: str | Sequence[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Create a new configuration item.

        Args:
            name: The setting name.
            apps: Which apps this applies to ("*" for all, or app names).
            default: Default value.
            help_: Short help text.
            description: Long description.
            type_: Type for casting values.
            validate: Validation/transformation function.
            title: Human-readable title.
            choices: Available choices.
            action: argparse action.
            flags: CLI flags.
            schema: JSON schema overrides.
            nargs: argparse nargs.
            nullable: Whether the setting accepts None. Auto-detected from
                default when not specified.
            hidden: Whether to hide from help output.
            hooks: Change callbacks.
            group: Deprecated, use apps instead.
            **kwargs: Additional arguments (e.g., version, const, filter, keys).
        """
        self.name = name
        self._apps = {apps} if isinstance(apps, str) else set(apps)
        self.default = default
        self.title = title or self.name.replace("_", " ")
        self.help = help_
        self.description = description
        self._choices = choices
        self.type = type_ or type(default)
        self.validate = validate
        self.action = action or TYPE_ACTIONS.get(self.type)
        self.flags = flags if flags is not None else [f"--{name.replace('_', '-')}"]
        self.nullable = nullable if nullable is not None else default is None
        self._schema_overrides: dict[str, Any] = dict(schema or {})
        self.nargs = nargs
        self.hidden = to_filter(hidden)
        self.hooks = hooks or []
        self.kwargs = kwargs

    def applies_to(self, app: str | None) -> bool:
        """Check if this setting applies to the given app.

        Args:
            app: The application name to check.

        Returns:
            True if this setting applies to the app.
        """
        return "*" in self._apps or app in self._apps

    @cached_property
    def choices(self) -> list[Any] | dict | None:
        """Compute the setting's available options."""
        if callable(self._choices):
            return self._choices()
        return self._choices

    @cached_property
    def schema(self) -> dict[str, Any]:
        """Return a JSON schema property for the config item."""
        # Start with base type information
        schema_type = _SCHEMA_TYPES.get(self.type)
        schema: dict[str, Any] = {}

        if schema_type is not None:
            if self.nullable:
                schema["type"] = [schema_type, "null"]
            else:
                schema["type"] = schema_type

        # Add description and default
        schema["description"] = self.help
        if self.default is not None:
            schema["default"] = self.default

        # Apply user-provided overrides
        schema.update(self._schema_overrides)

        # Add choices/enum constraints
        if self.choices:
            choices_list = (
                list(self.choices.keys())
                if isinstance(self.choices, dict)
                else list(self.choices)
            )
            if self.nargs == "*" or "items" in schema:
                schema.setdefault("items", {})["enum"] = choices_list
            else:
                enum_values = list(choices_list)
                if self.nullable:
                    enum_values.append(None)
                schema["enum"] = enum_values

        return schema

    @cached_property
    def menu(self) -> MenuItem:
        """Return a menu item for the setting."""
        from apptk.commands import get_cmd
        from apptk.widgets.menus import MenuItem

        choices = (self.choices or self.schema.get("enum", [])) or []
        if isinstance(choices, dict):
            choices = list(choices.keys())

        if choices:
            return MenuItem(
                self.title.capitalize(),
                children=[
                    MenuItem.from_cmd(cmd)
                    for cmd in sorted(
                        (
                            get_cmd(f"set-{self.name.replace('_', '-')}-{choice}")
                            for choice in choices
                        ),
                        key=lambda x: x.menu_title,
                    )
                ],
                description=self.help,
            )
        elif self.type in (bool, int):
            return MenuItem.from_cmd(f"toggle-{self.name.replace('_', '-')}")
        else:
            raise NotImplementedError

    @property
    def parser_args(self) -> tuple[list[str], dict[str, Any]]:
        """Return arguments for argparse.ArgumentParser.add_argument()."""
        if self.flags is not None and not self.flags:
            return [], {}

        args = self.flags or [self.name]
        kwargs: dict[str, Any] = {
            "action": self.action,
            "help": argparse.SUPPRESS if self.hidden() else self.help,
        }

        if self.nargs:
            kwargs["nargs"] = self.nargs
        if self.type is not None and self.name != "version":
            kwargs["type"] = self.type
        if self.choices:
            choices_list = (
                list(self.choices.keys())
                if isinstance(self.choices, dict)
                else self.choices
            )
            kwargs["choices"] = choices_list
        if "version" in self.kwargs:
            kwargs["version"] = self.kwargs["version"]
        if "const" in self.kwargs:
            kwargs["const"] = self.kwargs["const"]

        return args, kwargs

    def __repr__(self) -> str:
        """Represent a Setting instance as a string."""
        nullable = " nullable" if self.nullable else ""
        return f"<Setting {self.name}: {self.type}{nullable} apps={self._apps}>"
