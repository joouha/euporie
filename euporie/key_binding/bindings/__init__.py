"""Defines sets of key-bindings."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:

    from typing import Dict, List, Tuple, Union

    from prompt_toolkit.keys import Keys

    KeyBindingDefs = Dict[
        str,
        Union[
            List[Union[Tuple[Union[Keys, str], ...], Keys, str]],
            Union[Tuple[Union[Keys, str], ...], Keys, str],
        ],
    ]
