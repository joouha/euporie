# -*- coding: utf-8 -*-
from typing import Callable, Optional, Union

from prompt_toolkit.filters import FilterOrBool
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.keys import Keys


class KeyBindingsInfo(KeyBindings):
    details = {}

    def add(
        self,
        *keys: Union[Keys, str],
        filter: FilterOrBool = True,
        eager: FilterOrBool = False,
        is_global: FilterOrBool = False,
        save_before: Callable[["KeyPressEvent"], bool] = (lambda e: True),
        record_in_macro: FilterOrBool = True,
        key_str: Optional[str] = None,
        group: Optional[str] = "None",
        desc: Optional[str] = None,
    ):
        if desc is not None:
            self.details.setdefault(group, {}).setdefault(desc, {})[
                key_str or keys
            ] = None
        return super().add(
            *keys,
            filter=filter,
            eager=eager,
            is_global=is_global,
            save_before=save_before,
            record_in_macro=record_in_macro,
        )
