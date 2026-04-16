from collections.abc import Callable, Iterable

from apptk.completion import CompleteEvent, Completer, Completion
from apptk.document import Document

__all__ = [
    "ExecutableCompleter",
    "PathCompleter",
]

class PathCompleter(Completer):
    only_directories: bool
    get_paths: Callable[[], list[str]] | None
    file_filter: Callable[[str], bool] | None
    min_input_len: int
    expanduser: bool
    def __init__(
        self,
        only_directories: bool = False,
        get_paths: Callable[[], list[str]] | None = None,
        file_filter: Callable[[str], bool] | None = None,
        min_input_len: int = 0,
        expanduser: bool = False,
    ) -> None: ...
    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]: ...

class ExecutableCompleter(PathCompleter):
    def __init__(self) -> None: ...
