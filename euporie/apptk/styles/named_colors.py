"""Contain data reference dictionaries for value lookups."""

from prompt_toolkit.styles.named_colors import NAMED_COLORS

# Extend named colors to unclude lower-case names
NAMED_COLORS.update({k.lower(): v for k, v in NAMED_COLORS.items()})
