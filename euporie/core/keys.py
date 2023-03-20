"""Define KeyBindings wrapper which keeps track of key binding descriptions."""

from aenum import extend_enum
from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES
from prompt_toolkit.keys import Keys

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

# CSI-u control+key
ANSI_SEQUENCES["\x1b[97;5u"] = Keys.ControlA  # type: ignore
ANSI_SEQUENCES["\x1b[98;5u"] = Keys.ControlB  # type: ignore
ANSI_SEQUENCES["\x1b[99;5u"] = Keys.ControlC  # type: ignore
ANSI_SEQUENCES["\x1b[100;5u"] = Keys.ControlD  # type: ignore
ANSI_SEQUENCES["\x1b[101;5u"] = Keys.ControlE  # type: ignore
ANSI_SEQUENCES["\x1b[102;5u"] = Keys.ControlF  # type: ignore
ANSI_SEQUENCES["\x1b[103;5u"] = Keys.ControlG  # type: ignore
ANSI_SEQUENCES["\x1b[104;5u"] = Keys.ControlH  # type: ignore
ANSI_SEQUENCES["\x1b[105;5u"] = Keys.ControlI  # type: ignore
ANSI_SEQUENCES["\x1b[106;5u"] = Keys.ControlJ  # type: ignore
ANSI_SEQUENCES["\x1b[107;5u"] = Keys.ControlK  # type: ignore
ANSI_SEQUENCES["\x1b[108;5u"] = Keys.ControlL  # type: ignore
ANSI_SEQUENCES["\x1b[109;5u"] = Keys.ControlM  # type: ignore
ANSI_SEQUENCES["\x1b[110;5u"] = Keys.ControlN  # type: ignore
ANSI_SEQUENCES["\x1b[111;5u"] = Keys.ControlO  # type: ignore
ANSI_SEQUENCES["\x1b[112;5u"] = Keys.ControlP  # type: ignore
ANSI_SEQUENCES["\x1b[113;5u"] = Keys.ControlQ  # type: ignore
ANSI_SEQUENCES["\x1b[114;5u"] = Keys.ControlR  # type: ignore
ANSI_SEQUENCES["\x1b[115;5u"] = Keys.ControlS  # type: ignore
ANSI_SEQUENCES["\x1b[116;5u"] = Keys.ControlT  # type: ignore
ANSI_SEQUENCES["\x1b[117;5u"] = Keys.ControlU  # type: ignore
ANSI_SEQUENCES["\x1b[118;5u"] = Keys.ControlV  # type: ignore
ANSI_SEQUENCES["\x1b[119;5u"] = Keys.ControlW  # type: ignore
ANSI_SEQUENCES["\x1b[120;5u"] = Keys.ControlX  # type: ignore
ANSI_SEQUENCES["\x1b[121;5u"] = Keys.ControlY  # type: ignore
ANSI_SEQUENCES["\x1b[122;5u"] = Keys.ControlZ  # type: ignore
ANSI_SEQUENCES["\x1b[27;2;9~"] = Keys.BackTab  # type: ignore
ANSI_SEQUENCES["\x1b[9;2u"] = Keys.BackTab  # type: ignore
