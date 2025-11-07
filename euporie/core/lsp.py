"""Defines a simple LSP client."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from prompt_toolkit.utils import Event

from euporie.core.async_utils import get_or_create_loop, run_coro_async, run_coro_sync

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Sequence
    from typing import Any


log = logging.getLogger(__name__)


_COMPLETION_TYPES = {
    1: "text",
    2: "method",
    3: "function",
    4: "constructor",
    5: "field",
    6: "variable",
    7: "class",
    8: "interface",
    9: "module",
    10: "property",
    11: "unit",
    12: "value",
    13: "enum",
    14: "keyword",
    15: "snippet",
    16: "color",
    17: "file",
    18: "reference",
    19: "folder",
    20: "enum_member",
    21: "constant",
    22: "struct",
    23: "event",
    24: "operator",
    25: "type_parameter",
}


def range_to_slice(
    start_line: int, start_char: int, end_line: int, end_char: int, text: str
) -> slice:
    """Convert a line/character ranger to a slice."""
    start_pos = start_char
    end_pos = end_char
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        len_line = len(line)
        if i < start_line:
            start_pos += len_line
        if i < end_line:
            end_pos += len_line
        else:
            break
    return slice(start_pos, end_pos)


class LspCell(NamedTuple):
    """An LSP client's representation of a cell."""

    id: str
    idx: int
    path: Path
    kind: str
    language: str
    text: str
    execution_count: int
    metadata: dict[str, Any] | None = None


class LspClient:
    """A client for communicating with LSP servers."""

    def __init__(
        self,
        name: str,
        command: str,
        languages: Sequence[str] | None = None,
        settings: dict | None = None,
    ) -> None:
        """Initialize the LSP client."""
        self.name = name
        self.command = command
        self.languages = set(languages) if languages else set()
        self.settings = settings or {}
        self.started = False

        # The current RPC message ID
        self._msg_id = 0
        # References to callbacks for expected message responses
        self._msg_callbacks: dict[int, Callable[[Any], Coroutine[Any, Any, None]]] = {}
        # Change version numbers for opened documents
        self._doc_versions: dict[Path, int] = {}
        # Futures for change events, allowing debouncing changes
        self._change_futures: dict[Path, asyncio.Future[None]] = {}
        # Holds diagnostic reports (NOTE: uses URI string from response as key)
        self.reports: dict[str, list] = {}

        self.initialized = asyncio.Event()

        # Server capability flags. None = not sure yet
        self.can_hover: bool | None = None
        self.can_format: bool | None = None
        self.can_complete: bool | None = None
        self.can_signature: bool | None = None
        # `open_doc`, `change_doc` and `close_doc` are mandatory for LSP servers
        self.can_open_doc: bool | None = True
        self.can_close_doc: bool | None = True
        self.can_change_doc: bool | None = True
        self.can_change_doc_incr: bool | None = None
        self.can_save_doc: bool | None = None
        self.can_will_save_doc: bool | None = None
        self.can_open_nb: bool | None = None
        self.can_change_nb: bool | None = None
        self.can_change_nb_langs: list[str] = []

        self._request_handlers = {
            "window/logMessage": self.log_message,
            "textDocument/publishDiagnostics": self.diagnostics,
        }

        self.on_diagnostics = Event(self)

        # Ensure LSP servers get shutdown at exit
        self.on_exit = Event(self)

        self.loop = get_or_create_loop("lsp")

    def __repr__(self) -> str:
        """Return a string representation of the LSP client."""
        return f"{self.__class__.__name__}(name={self.name})"

    @property
    def next_msg_id(self) -> int:
        """Get and increment the RPC message ID."""
        self._msg_id += 1
        return self._msg_id

    def start(self, root: Path | None = None) -> None:
        """Start the LSP server."""
        if not self.started:
            # Start lsp server process and monitor it on event loop in thread
            run_coro_sync(self.start_(root), self.loop)

    async def start_(self, root: Path | None = None) -> None:
        """Launch the LSP server subprocess."""
        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            # stderr=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        self.monitor_stdout_task = self.loop.create_task(self._monitor_stdout())
        self.monitor_stderr_task = self.loop.create_task(self._monitor_stderr())
        self.started = True

        # Tell the server to initialize
        await self.initialize(root)

    async def _monitor_stderr(self) -> None:
        """Log LSP server standard error output."""
        while stderr := self.process.stderr:
            line = await stderr.readline()
            if line:
                log.info(line.decode().rstrip())
            else:
                break

    async def _monitor_stdout(self) -> None:
        """Retrieve and parse responses."""
        buffer = b""
        length = 0
        # mime: str = None
        charset: str = "utf-8"

        while stdout := self.process.stdout:
            if buffer.startswith(b"Content-Length: "):
                line_end = buffer.find(b"\r\n")
                _, _, _length = buffer[:line_end].partition(b": ")
                length = int(_length)
                buffer = buffer[line_end + 2 :]
                continue

            if buffer.startswith(b"Content-Type: "):
                line_end = buffer.find(b"\r\n")
                _, _, _content_type = buffer[:line_end].partition(b": ")
                # TODO - get mime & encoding
                # mime =
                # charset =
                buffer = buffer[line_end + 2 :]
                continue

            if buffer.startswith(b"\r\n"):
                buffer = buffer[2:]
                continue

            if length and len(buffer) >= length:
                content = buffer[:length]
                buffer = buffer[length:]
                length = 0
                await self.process_msg(json.loads(content.decode(charset)))
                continue

            else:
                # Read a (large) chunk of the server's stdout
                line = await stdout.read(1024 * 1024)
                if line:
                    buffer += line
                else:
                    break

    async def process_msg(self, data: dict) -> None:
        """Process an incoming message from the LSP server."""
        # log.debug("%s received message %s", self, data)
        if msg_id := data.get("id"):
            if callback := self._msg_callbacks.get(msg_id):
                try:
                    await callback(data.get("result", {}))
                except Exception:
                    log.exception("An error occurred executing the LSP callback")
                finally:
                    del self._msg_callbacks[msg_id]

                return

        elif method := data.get("method"):
            # A request from the server
            if handler := self._request_handlers.get(method):
                handler(data.get("params", {}))

            else:
                log.info(data)

        else:
            # Some other response from the server
            log.info(data)

    async def send_msg(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        cb: Callable[[Any], Coroutine[Any, Any, None]] | None = None,
    ) -> int:
        """Send a message to the LSP server, returning the sent message's ID."""
        msg_id = self.next_msg_id
        msg: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            msg["params"] = params
        if cb:
            msg["id"] = msg_id
        body = json.dumps(msg, separators=(",", ":"))
        # log.debug("Sending %s message %s", self, body)
        data = f"Content-Length: {len(body)}\r\n\r\n{body}"
        if stdin := self.process.stdin:
            stdin.write(data.encode())
            await stdin.drain()
        else:
            log.error("Unexpectedly lost connection with %s", self)
        if callable(cb):
            self._msg_callbacks[msg_id] = cb
        return msg_id

    async def initialize(self, root: Path | None = None) -> None:
        """Initiate the LSP server."""
        if not self.initialized.is_set():
            if root is None:
                root = Path.cwd()
            await self.send_msg(
                method="initialize",
                params={
                    "trace": "off",
                    "processId": os.getpid(),
                    "capabilities": {
                        "workspace": {
                            "applyEdit": False,
                            "fileOperations": {
                                "dynamicRegistration": False,
                                "didCreate": False,
                                "willCreate": False,
                                "didRename": False,
                                "willRename": False,
                                "didDelete": False,
                                "willDelete": False,
                            },
                        },
                        "textDocument": {
                            "willSave": True,
                            "didSave": True,
                        },
                        "notebookDocument": {
                            "synchronization": {"executionSummarySupport": True}
                        },
                        "documentSelector": [
                            {"scheme": "file"},
                            {"scheme": "untitled"},
                        ],
                    },
                    "rootUri": root.as_uri(),
                    "clientInfo": {"name": "euporie", "version": "2.7.0"},
                },
                cb=self._on_initialize_response,
            )

    async def _on_initialize_response(self, rsp: dict[str, Any]) -> None:
        server_info = rsp.get("serverInfo", {})
        self.server_name = server_info.get("name")
        self.server_version = server_info.get("version")

        capabilities = rsp.get("capabilities", {})

        _change_options = capabilities.get("textDocumentSync", {})
        if isinstance(_change_options, int):
            _change_kind = _change_options
            _change_options = {}
        else:
            _change_kind = _change_options.get("change")
        if isinstance(_change_options.get("save"), bool):
            _save_options = {}
        else:
            _save_options = _change_options.get("save", {})

        self.can_hover = (
            "hoverProvider" in capabilities
            and capabilities["hoverProvider"] is not False
        )
        self.can_format = (
            "documentFormattingProvider" in capabilities
            and capabilities["documentFormattingProvider"] is not False
        )
        self.can_complete = (
            "completionProvider" in capabilities
            and capabilities["completionProvider"] is not False
        )
        self.can_signature = (
            "signatureHelpProvider" in capabilities
            and capabilities["signatureHelpProvider"] is not False
        )

        self.can_change_doc = "textDocumentSync" in capabilities and (
            _change_kind is None or _change_kind > 0
        )
        self.can_change_doc_incr = _change_kind == 2
        self.can_save_doc = "save" in _change_options
        self.can_save_doc_text = _save_options.get("includeText", True)
        self.can_will_save_doc = "willSave" in _change_options

        _nb_change_options = capabilities.get("notebookDocumentSync", {})
        self.can_open_nb = self.can_change_nb = self.can_close_nb = bool(
            _nb_change_options
        )
        # self.can_change_nb = any(
        #     "notebook" in selector
        #     for selector in _nb_change_options.get("notebookSelector", [])
        # )
        self.can_change_nb_langs = [
            cell_selector.get("language")
            for nb_selector in _nb_change_options.get("notebookSelector", [])
            for cell_selector in nb_selector.get("cells", [])
            if cell_selector.get("language")
        ]
        self.can_save_nb = _nb_change_options.get("save")

        # for name, value in rsp.get("capabilities", {}).items():
        #     log.debug("%s: %s: %s", self, name, value)

        await self.send_msg(method="initialized", params={})
        self.initialized.set()

        # Send settings
        await self.send_msg(
            method="workspace/didChangeConfiguration",
            params={"settings": self.settings},
        )

    def exit(self) -> asyncio.Future[None]:
        """Tell the server to exit."""
        return run_coro_async(self.exit_(), self.loop)

    async def exit_(self, timeout: int = 1) -> None:
        """Tell the server to exit."""
        log.debug("%s exiting", self)
        self.on_exit.fire()
        event = asyncio.Event()

        async def _cb(result: dict | None) -> None:
            await self.send_msg(method="exit")
            event.set()

        await self.send_msg(method="shutdown", cb=_cb)

        try:
            await asyncio.wait_for(event.wait(), timeout)
        except asyncio.TimeoutError:
            log.debug("Timed out waiting for %s shutdown response", self)

        try:
            await asyncio.wait_for(self.process.wait(), timeout=1)
        except TimeoutError:
            self.process.kill()
        log.debug("%s exited", self)

    def open_doc(self, path: Path, language: str, text: str) -> None:
        """Tell the server we have opened a document file."""
        # "An open notification must not be sent more than once without a corresponding
        #  close notification send before"
        if path in self._doc_versions:
            return
        # else:
        #     log.debug("%s opening %s", self, path)
        if self.languages and language not in self.languages:
            return
        self._doc_versions[path] = 0
        run_coro_async(
            self.send_msg(
                method="textDocument/didOpen",
                params={
                    "textDocument": {
                        "uri": path.as_uri(),
                        "languageId": language.lower(),
                        "version": 0,
                        "text": text,
                    }
                },
            ),
            self.loop,
        )

    def open_nb(
        self, path: Path, cells: Sequence[LspCell], metadata: dict[str, Any] | None
    ) -> None:
        """Tell the server we have opened a notebook file."""
        if not self.can_open_nb:
            return
        self._doc_versions[path] = 0
        params: dict[str, Any] = {
            "notebookDocument": {
                "uri": path.as_uri(),
                "notebookType": "jupyter-notebook",
                "version": 0,
                # "metadata": metadata or {},
                "cells": [],
            },
            "cellTextDocuments": [],
        }
        langs = self.can_change_nb_langs
        lsp_notebook_cell: dict[str, Any]
        for cell in cells:
            if langs and cell.language not in langs:
                continue
            self._doc_versions[cell.path] = 0
            uri = cell.path.as_uri()
            params["notebookDocument"]["cells"].append(
                lsp_notebook_cell := {
                    "kind": 2 if cell.kind == "code" else 1,
                    "document": uri,
                    # "metadata": cell.metadata,
                }
            )
            if cell.execution_count:
                lsp_notebook_cell["executionSummary"] = {
                    "executionOrder": cell.execution_count,
                    # "success": True,
                }
            params["cellTextDocuments"].append(
                {
                    "uri": uri,
                    "languageId": cell.language.lower(),
                    "version": 0,
                    "text": cell.text,
                }
            )
        run_coro_async(
            self.send_msg(
                method="notebookDocument/didOpen",
                params=params,
            ),
            self.loop,
        )

    def change_doc(
        self, path: Path, language: str, text: str, debounce: bool = True
    ) -> None:
        """Tell the server we have changed a document file."""
        if (langs := self.languages) and language not in langs:
            return

        if path in self._change_futures:
            self._change_futures[path].cancel()
            del self._change_futures[path]

        async def _notify_change() -> None:
            if debounce:
                await asyncio.sleep(0.25)
            self._doc_versions[path] += 1
            await self.send_msg(
                method="textDocument/didChange",
                params={
                    "textDocument": {
                        "uri": path.as_uri(),
                        "version": self._doc_versions[path],
                    },
                    "contentChanges": [
                        {
                            # "range": {
                            #     "start": {"line": 0, "character": 0},
                            #     "end": {"line": 6, "character": 0},
                            # },
                            "text": text,
                        }
                    ],
                },
            )

        self._change_futures[path] = run_coro_async(_notify_change(), self.loop)
        if not debounce:
            self._change_futures[path].result()

    def change_nb_meta(self, path: Path, metadata: dict[str, Any]) -> None:
        """Notify server of a change in a notebook metadata."""
        if not self.can_change_nb:
            return
        # Update versions
        self._doc_versions[path] += 1
        run_coro_async(
            self.send_msg(
                method="notebookDocument/didChange",
                params={
                    "notebookDocument": {
                        "uri": path.as_uri(),
                        "version": self._doc_versions[path],
                    },
                    "change": {"metadata": metadata},
                },
            ),
            self.loop,
        )

    def change_nb_add(self, path: Path, cells: Sequence[LspCell]) -> None:
        """Notify server of cells added to notebook."""
        if not self.can_change_nb:
            return
        # Update notebook version
        self._doc_versions[path] += 1
        # Set RPC parameters
        change: dict[str, Any]  # TODO - use typed dicts?
        params = {
            "notebookDocument": {
                "uri": path.as_uri(),
                "version": self._doc_versions[path],
            },
            "change": {
                "cells": (
                    change := {
                        "structure": {
                            "array": {
                                "start": min(cell.idx for cell in cells),
                                "deleteCount": 0,
                                "cells": [],
                            },
                            "didOpen": [],
                        },
                        "data": [],
                    }
                )
            },
        }
        langs = self.can_change_nb_langs
        lsp_notebook_cell: dict[str, Any]
        for cell in cells:
            # If specified, only sync cells with the languages the server has requested
            if langs and cell.language not in langs:
                continue
            self._doc_versions[cell.path] = 0
            lsp_notebook_cell = {
                "kind": 2 if cell.kind == "code" else 1,
                "document": cell.path.as_uri(),
                # "metadata": cell.metadata,
            }
            if cell.execution_count:
                lsp_notebook_cell["executionSummary"] = {
                    "executionOrder": cell.execution_count,
                    # "success": True,
                }
            change["structure"]["array"]["cells"].append(lsp_notebook_cell)
            change["structure"]["didOpen"].append(
                {
                    "uri": cell.path.as_uri(),
                    "languageId": cell.language,
                    "version": self._doc_versions[cell.path],
                    "text": cell.text,
                }
            )
            change["data"].append(lsp_notebook_cell)
        # Run RPC call
        run_coro_async(
            self.send_msg(
                method="notebookDocument/didChange",
                params=params,
            ),
            self.loop,
        )

    def change_nb_edit(
        self, path: Path, cells: Sequence[LspCell], debounce: bool = True
    ) -> None:
        """Notify server of a change in  notebook cells."""
        if not self.can_change_nb:
            return

        if path in self._change_futures:
            self._change_futures[path].cancel()
            del self._change_futures[path]

        async def _notify_change() -> None:
            if debounce:
                await asyncio.sleep(0.25)
            self._doc_versions[path] += 1

            change: dict[str, list[dict]]
            params = {
                "notebookDocument": {
                    "uri": path.as_uri(),
                    "version": self._doc_versions[path],
                },
                "change": {"cells": (change := {"data": [], "textContent": []})},
            }
            langs = self.can_change_nb_langs
            lsp_notebook_cell: dict[str, Any]
            for cell in cells:
                self._doc_versions[cell.path] += 1
                # If specified, only sync cells with the languages the server has requested
                if langs and cell.language not in langs:
                    continue
                change["data"].append(
                    lsp_notebook_cell := {
                        "kind": 2 if cell.kind == "code" else 1,
                        "document": cell.path.as_uri(),
                        # "metadata": cell.metadata,
                    }
                )
                if cell.execution_count:
                    lsp_notebook_cell["executionSummary"] = {
                        "executionOrder": cell.execution_count,
                        # "success": True,
                    }
                change["textContent"].append(
                    {
                        "document": {
                            "uri": cell.path.as_uri(),
                            "version": self._doc_versions[cell.path],
                        },
                        "changes": [{"text": cell.text}],
                    }
                )

            # Run RPC call
            await self.send_msg(
                method="notebookDocument/didChange",
                params=params,
            )

        self._change_futures[path] = run_coro_async(_notify_change(), self.loop)
        if not debounce:
            self._change_futures[path].result()

    def change_nb_delete(self, path: Path, cells: Sequence[LspCell]) -> None:
        """Notify server of cells removed from a notebook."""
        if not self.can_change_nb:
            return
        # Update versions
        self._doc_versions[path] += 1
        langs = self.can_change_nb_langs
        for cell in cells:
            # If specified, only sync cells with the languages the server has requested
            if langs and cell.language not in langs:
                continue
            self._cleanup_path(cell.path)
        # Set RPC parameters
        run_coro_async(
            self.send_msg(
                method="notebookDocument/didChange",
                params={
                    "notebookDocument": {
                        "uri": path.as_uri(),
                        "version": self._doc_versions[path],
                    },
                    "change": {
                        "cells": {
                            "structure": {
                                "array": {
                                    "start": min(cell.idx for cell in cells),
                                    "deleteCount": len(cells),
                                },
                                "didClose": [
                                    {"uri": cell.path.as_uri()} for cell in cells
                                ],
                            }
                        }
                    },
                },
            ),
            self.loop,
        )

    def will_save_doc(self, path: Path) -> None:
        """Tell the server we will save a document file."""
        if self.can_will_save_doc:
            run_coro_async(
                self.send_msg(
                    method="textDocument/willSave",
                    params={
                        "textDocument": {"uri": path.as_uri()},
                        "reason": 1,  # Manual save
                    },
                ),
                self.loop,
            )

    def will_save_nb(self, path: Path) -> None:
        """Tell the server we will save a notebook file."""

    def save_doc(self, path: Path, text: str) -> None:
        """Tell the server we saved a text document."""
        if self.can_save_doc:
            run_coro_async(
                self.send_msg(
                    method="textDocument/didSave",
                    params={
                        "textDocument": {"uri": path.as_uri()},
                        **({"text": text} if self.can_save_doc_text else {}),
                    },
                ),
                self.loop,
            )

    def save_nb(self, path: Path) -> None:
        """Tell the server we saved a notebook."""
        run_coro_async(
            self.send_msg(
                method="notebookDocument/didSave",
                params={
                    "notebookDocument": {"uri": path.as_uri()},
                },
            ),
            self.loop,
        )

    def _cleanup_path(self, path: Path) -> None:
        try:
            del self._doc_versions[path]
        except KeyError:
            pass
        try:
            del self._change_futures[path]
        except KeyError:
            pass
        try:
            del self.reports[path.as_uri()]
        except KeyError:
            pass

    def close_doc(self, path: Path) -> None:
        """Tell the server we have closed a document file."""
        # log.debug("%s closing %s", self, path)
        self._cleanup_path(path)
        run_coro_async(
            self.send_msg(
                method="textDocument/didClose",
                params={
                    "textDocument": {"uri": path.as_uri()},
                },
            ),
            self.loop,
        )

    def close_nb(self, path: Path, cells: Sequence[LspCell]) -> None:
        """Tell the server we closed a notebook document."""
        # log.debug("%s closing %s", self, path)
        params = {"notebookDocument": {"uri": path.as_uri()}, "cellTextDocuments": []}
        for cell in cells:
            self._cleanup_path(cell.path)
            # params["cellTextDocuments"].append({"uri": cell_path.as_uri()})
        self._cleanup_path(path)
        run_coro_async(
            self.send_msg(method="notebookDocument/didClose", params=params), self.loop
        )

    def complete(
        self,
        path: Path,
        line: int,
        char: int,
        timeout: int = 5,
    ) -> list[dict[str, str]]:
        """Trigger a LSP completion request."""
        if not self.can_complete:
            return []
        return run_coro_sync(self.complete_(path, line, char, timeout), self.loop)

    async def complete_(
        self, path: Path, line: int, char: int, timeout: int = 5
    ) -> list[dict[str, Any]]:
        """Request a completion from the LSP server."""
        if not self.can_complete:
            return []
        results = []
        event = asyncio.Event()

        async def _cb(rsp: dict[str, Any]) -> None:
            for item in rsp.get("items", []):
                results.append(
                    {
                        "text": item["insertText"],
                        "display": item.get("label"),
                        # "start_position": rel_start_position,
                        "display_meta": _COMPLETION_TYPES.get(item.get("kind")),
                    }
                )
            event.set()

        await self.send_msg(
            method="textDocument/completion",
            params={
                "textDocument": {"uri": path.as_uri()},
                "position": {"line": line, "character": char},
                "context": {
                    "triggerKind": 1  # Manually triggered
                },
            },
            cb=_cb,
        )

        try:
            await asyncio.wait_for(event.wait(), timeout)
        except asyncio.TimeoutError:
            log.debug("Timed out waiting for %s completion response", self)

        return results

    def hover(self, path: Path, line: int, char: int, timeout: int = 1) -> dict:
        """Trigger a LSP hover request."""
        if not self.can_hover:
            return {}
        return run_coro_sync(self.hover_(path, line, char, timeout), self.loop)

    async def hover_(self, path: Path, line: int, char: int, timeout: int = 5) -> dict:
        """Request hover text from the LSP server."""
        if not self.can_hover:
            return {}
        result = {}
        event = asyncio.Event()

        async def _cb(rsp: dict[str, Any]) -> None:
            if rsp:
                contents = rsp.get("contents", {})
                mime = "text/markdown"
                if isinstance(contents, str):
                    data = contents
                elif "language" in contents:
                    language = contents.get("language", "")
                    value = contents.get("value", "")
                    data = f"```${language}\n${value}\n```"
                elif "kind" in contents:
                    if contents["kind"] == "plaintext":
                        mime = "text/plain"
                    data = contents.get("value", "")
                if data:
                    result.update({mime: data})
            event.set()

        await self.send_msg(
            method="textDocument/hover",
            params={
                "textDocument": {"uri": path.as_uri()},
                "position": {"line": line, "character": char},
            },
            cb=_cb,
        )
        try:
            await asyncio.wait_for(event.wait(), timeout)
        except asyncio.TimeoutError:
            log.debug("Timed out waiting for %s hover response", self)

        return result

    def signature(
        self, path: Path, line: int, char: int, timeout: int = 1
    ) -> dict[str, object] | None:
        """Trigger a LSP signature request."""
        if not self.can_signature:
            return None
        return run_coro_sync(
            self.signature_(path, line, char, timeout=timeout), self.loop
        )

    async def signature_(
        self, path: Path, line: int, char: int, timeout: int = 5
    ) -> dict[str, object] | None:
        """Request a signature from the LSP server."""
        if not self.can_signature:
            return None
        result = {}
        event = asyncio.Event()

        async def _cb(rsp: dict[str, Any]) -> None:
            mime = "text/markdown"
            contents = rsp.get("contents", {})
            if isinstance(contents, str):
                data = contents
            elif "language" in contents:
                language = contents.get("language", "")
                value = contents.get("value", "")
                data = f"```${language}\n${value}\n```"
            elif "kind" in contents:
                if contents["kind"] == "plaintext":
                    mime = "text/plain"
                data = contents.get("value", "")
            result.update({"found": True, "data": {mime: data}})
            event.set()

        await self.send_msg(
            method="textDocument/signatureHelp",
            params={
                "textDocument": {
                    "uri": path.as_uri(),
                    "version": self._doc_versions[path],
                },
                "position": {"line": line, "character": char},
            },
            cb=_cb,
        )
        try:
            await asyncio.wait_for(event.wait(), timeout)
        except asyncio.TimeoutError:
            log.debug("Timed out waiting for %s signature response", self)

        return result

    def format(
        self, path: Path, tab_size: int = 4, spaces: bool = True, timeout: int = 1
    ) -> list[dict] | None:
        """Request LSP document formatting."""
        if not self.can_format:
            return []
        return run_coro_sync(self.format_(path, timeout=timeout), self.loop)

    async def format_(
        self, path: Path, tab_size: int = 4, spaces: bool = True, timeout: int = 5
    ) -> list[dict] | None:
        """Trigger a formatting request from the LSP."""
        if not self.can_format:
            return []
        result = []
        event = asyncio.Event()

        async def _cb(rsp: list) -> None:
            if rsp:
                result.extend(rsp)
            event.set()

        await self.send_msg(
            method="textDocument/formatting",
            params={
                "textDocument": {
                    "uri": path.as_uri(),
                    "version": self._doc_versions[path],
                },
                "options": {"tabSize": tab_size, "insertSpaces": spaces},
            },
            cb=_cb,
        )
        try:
            await asyncio.wait_for(event.wait(), timeout)
        except asyncio.TimeoutError:
            log.debug("Timed out waiting for %s format response", self)

        return result

    def log_message(self, params: dict[str, Any]) -> None:
        """Send a log message from the server to the log."""
        if msg := params.get("message"):
            msg_type = params.get("type", 2)
            level = (5 - msg_type) * 10
            log.log(level, msg)

    def diagnostics(self, params: dict[str, Any]) -> None:
        """Receive a diagnstics report from the server."""
        uri: str
        if uri := params.get("uri", ""):
            self.reports[uri] = params.get("diagnostics", [])
            self.on_diagnostics.fire()


KNOWN_LSP_SERVERS: dict[str, dict[str, Any]] = {
    # Custom additions
    "typos": {"command": ["typos-lsp"], "languages": set()},
    # Helix's known LSPs
    "als": {"command": ["als"]},
    "ada-language-server": {"command": ["ada_language_server"], "languages": {"ada"}},
    "ada-gpr-language-server": {
        "command": ["ada_language_server", "--language-gpr"],
        "languages": {"ada"},
    },
    "angular": {
        "command": [
            "ngserver",
            "--stdio",
            "--tsProbeLocations",
            ".",
            "--ngProbeLocations",
            ".",
        ]
    },
    "awk-language-server": {"command": ["awk-language-server"], "languages": {"awk"}},
    "bash-language-server": {
        "command": ["bash-language-server", "start"],
        "languages": {"bash"},
    },
    "bass": {"command": ["bass", "--lsp"], "languages": {"bass"}},
    "bicep-langserver": {"command": ["bicep-langserver"], "languages": {"bicep"}},
    "bitbake-language-server": {
        "command": ["bitbake-language-server"],
        "languages": {"bitbake"},
    },
    "bufls": {"command": ["bufls", "serve"], "languages": {"protobuf"}},
    "cairo-language-server": {
        "command": ["cairo-language-server"],
        "languages": {"cairo"},
    },
    "circom-lsp": {"command": ["circom-lsp"], "languages": {"circom"}},
    "cl-lsp": {"command": ["cl-lsp", "stdio"], "languages": {"common-lisp"}},
    "clangd": {"command": ["clangd"], "languages": {"opencl", "cpp", "c"}},
    "clojure-lsp": {"command": ["clojure-lsp"], "languages": {"clojure"}},
    "cmake-language-server": {
        "command": ["cmake-language-server"],
        "languages": {"cmake"},
    },
    "crystalline": {"command": ["crystalline", "--stdio"], "languages": {"crystal"}},
    "cs": {
        "command": ["cs", "launch", "--contrib", "smithy-language-server", "--", "0"],
        "languages": {"smithy"},
    },
    "csharp-ls": {"command": ["csharp-ls"]},
    "cuelsp": {"command": ["cuelsp"], "languages": {"cue"}},
    "dart": {
        "command": ["dart", "language-server", "--client-id=helix"],
        "languages": {"dart"},
    },
    "dhall-lsp-server": {"command": ["dhall-lsp-server"], "languages": {"dhall"}},
    "docker-langserver": {
        "command": ["docker-langserver", "--stdio"],
        "languages": {"dockerfile"},
    },
    "docker-compose-langserver": {
        "command": ["docker-compose-langserver", "--stdio"],
        "languages": {"docker-compose"},
    },
    "dot-language-server": {
        "command": ["dot-language-server", "--stdio"],
        "languages": {"dot"},
    },
    "earthlyls": {"command": ["earthlyls"], "languages": {"earthfile"}},
    "elixir-ls": {
        "settings": {"elixirLS": {"dialyzerEnabled": False}},
        "command": ["elixir-ls"],
        "languages": {"heex", "elixir"},
    },
    "elm-language-server": {"command": ["elm-language-server"], "languages": {"elm"}},
    "elp": {"command": ["elp", "server"], "languages": {"erlang"}},
    "elvish": {"command": ["elvish", "-lsp"], "languages": {"elvish"}},
    "erlang-ls": {"command": ["erlang_ls"], "languages": {"erlang"}},
    "forc": {"command": ["forc", "lsp"], "languages": {"sway"}},
    "forth-lsp": {"command": ["forth-lsp"], "languages": {"forth"}},
    "fortls": {
        "command": ["fortls", "--lowercase_intrinsics"],
        "languages": {"fortran"},
    },
    "fsharp-ls": {
        "settings": {"AutomaticWorkspaceInit": True},
        "command": ["fsautocomplete"],
        "languages": {"fsharp"},
    },
    "gleam": {"command": ["gleam", "lsp"], "languages": {"gleam"}},
    "glsl_analyzer": {"command": ["glsl_analyzer"], "languages": {"glsl"}},
    "graphql-language-service": {
        "command": ["graphql-lsp", "server", "-m", "stream"],
        "languages": {"graphql"},
    },
    "haskell-language-server": {
        "command": ["haskell-language-server-wrapper", "--lsp"],
        "languages": {"cabal", "haskell"},
    },
    "hyprls": {"command": ["hyprls"], "languages": {"hyprlang"}},
    "idris2-lsp": {"command": ["idris2-lsp"], "languages": {"idris"}},
    "intelephense": {"command": ["intelephense", "--stdio"], "languages": {"php"}},
    "jdtls": {"command": ["jdtls"], "languages": {"java"}},
    "jedi": {"command": ["jedi-language-server"], "languages": {"python"}},
    "jq-lsp": {"command": ["jq-lsp"], "languages": {"jq"}},
    "jsonnet-language-server": {
        "command": ["jsonnet-language-server", "-t", "--lint"],
        "languages": {"jsonnet"},
    },
    "julia": {
        "timeout": 60,
        "command": [
            "julia",
            "--startup-file=no",
            "--history-file=no",
            "--quiet",
            "-e",
            "using LanguageServer; runserver()",
        ],
        "languages": {"julia"},
    },
    "koka": {
        "command": ["koka", "--language-server", "--lsstdio"],
        "languages": {"koka"},
    },
    "kotlin-language-server": {
        "command": ["kotlin-language-server"],
        "languages": {"kotlin"},
    },
    "lean": {"command": ["lean", "--server", "--memory=1024"], "languages": {"lean"}},
    "ltex-ls": {"command": ["ltex-ls"]},
    "markdoc-ls": {"command": ["markdoc-ls", "--stdio"], "languages": {"markdoc"}},
    "markdown-oxide": {"command": ["markdown-oxide"], "languages": {"markdown"}},
    "marksman": {"command": ["marksman", "server"], "languages": {"markdown"}},
    "metals": {
        "settings": {
            "isHttpEnabled": True,
            "metals": {
                "inlayHints": {
                    "typeParameters": {"enable": True},
                    "hintsInPatternMatch": {"enable": True},
                }
            },
        },
        "command": ["metals"],
        "languages": {"scala"},
    },
    "mesonlsp": {"command": ["mesonlsp", "--lsp"], "languages": {"meson"}},
    "mint": {"command": ["mint", "ls"], "languages": {"mint"}},
    "mojo-lsp": {"command": ["mojo-lsp-server"], "languages": {"mojo"}},
    "nil": {"command": ["nil"], "languages": {"nix"}},
    "nimlangserver": {"command": ["nimlangserver"], "languages": {"nim"}},
    "nimlsp": {"command": ["nimlsp"]},
    "nixd": {"command": ["nixd"], "languages": {"nix"}},
    "nls": {"command": ["nls"], "languages": {"nickel"}},
    "nu-lsp": {"command": ["nu", "--lsp"], "languages": {"nu"}},
    "ocamllsp": {"command": ["ocamllsp"], "languages": {"ocaml", "ocaml-interface"}},
    "ols": {"command": ["ols"], "languages": {"odin"}},
    "omnisharp": {
        "command": ["OmniSharp", "--languageserver"],
        "languages": {"c-sharp"},
    },
    "openscad-lsp": {"command": ["openscad-lsp", "--stdio"], "languages": {"openscad"}},
    "pasls": {"command": ["pasls"], "languages": {"pascal"}},
    "pbkit": {"command": ["pb", "lsp"], "languages": {"protobuf"}},
    "perlnavigator": {"command": ["perlnavigator", "--stdio"], "languages": {"perl"}},
    "pest-language-server": {
        "command": ["pest-language-server"],
        "languages": {"pest"},
    },
    "prisma-language-server": {
        "command": ["prisma-language-server", "--stdio"],
        "languages": {"prisma"},
    },
    "purescript-language-server": {
        "command": ["purescript-language-server", "--stdio"],
        "languages": {"purescript"},
    },
    "pylsp": {"command": ["pylsp"], "languages": {"snakemake", "python"}},
    "pyright": {"settings": {}, "command": ["pyright-langserver", "--stdio"]},
    "basedpyright": {"settings": {}, "command": ["basedpyright-langserver", "--stdio"]},
    "pylyzer": {"command": ["pylyzer", "--server"]},
    "qmlls": {"command": ["qmlls"], "languages": {"qml"}},
    "quint-language-server": {
        "command": ["quint-language-server", "--stdio"],
        "languages": {"quint"},
    },
    "r": {
        "command": ["R", "--no-echo", "-e", "languageserver::run()"],
        "languages": {"rmarkdown", "r"},
    },
    "racket": {
        "command": ["racket", "-l", "racket-langserver"],
        "languages": {"racket"},
    },
    "regols": {"command": ["regols"], "languages": {"rego"}},
    "rescript-language-server": {
        "command": ["rescript-language-server", "--stdio"],
        "languages": {"rescript"},
    },
    "robotframework_ls": {"command": ["robotframework_ls"], "languages": {"robot"}},
    "ruff": {"command": ["ruff", "server"], "languages": {"python"}},
    "serve-d": {"command": ["serve-d"], "languages": {"d"}},
    "slint-lsp": {"command": ["slint-lsp"], "languages": {"slint"}},
    "solargraph": {"command": ["solargraph", "stdio"], "languages": {"ruby"}},
    "solc": {"command": ["solc", "--lsp"], "languages": {"solidity"}},
    "sourcekit-lsp": {"command": ["sourcekit-lsp"], "languages": {"swift"}},
    "spade-language-server": {
        "command": ["spade-language-server"],
        "languages": {"spade"},
    },
    "svlangserver": {"command": ["svlangserver"], "languages": {"verilog"}},
    "swipl": {
        "command": [
            "swipl",
            "-g",
            "use_module(library(lsp_server))",
            "-g",
            "lsp_server:main",
            "-t",
            "halt",
            "--",
            "stdio",
        ],
        "languages": {"prolog"},
    },
    "superhtml": {"command": ["superhtml", "lsp"], "languages": {"html"}},
    "tailwindcss-ls": {"command": ["tailwindcss-language-server", "--stdio"]},
    "taplo": {"command": ["taplo", "lsp", "stdio"], "languages": {"toml"}},
    "templ": {"command": ["templ", "lsp"], "languages": {"templ"}},
    "terraform-ls": {
        "command": ["terraform-ls", "serve"],
        "languages": {"tfvars", "hcl"},
    },
    "texlab": {"command": ["texlab"], "languages": {"latex", "bibtex"}},
    "typespec": {"command": ["tsp-server", "--stdio"], "languages": {"typespec"}},
    "vala-language-server": {
        "command": ["vala-language-server"],
        "languages": {"vala"},
    },
    "vale-ls": {"command": ["vale-ls"]},
    "vhdl_ls": {"command": ["vhdl_ls"], "languages": {"vhdl"}},
    "vlang-language-server": {"command": ["v-analyzer"], "languages": {"v"}},
    "vscode-css-language-server": {
        "settings": {"provideFormatter": True, "css": {"validate": {"enable": True}}},
        "command": ["vscode-css-language-server", "--stdio"],
        "languages": {"scss", "css"},
    },
    "vscode-html-language-server": {
        "settings": {"provideFormatter": True},
        "command": ["vscode-html-language-server", "--stdio"],
        "languages": {"html"},
    },
    "vscode-json-language-server": {
        "settings": {"provideFormatter": True, "json": {"validate": {"enable": True}}},
        "command": ["vscode-json-language-server", "--stdio"],
        "languages": {"jsonc", "json"},
    },
    "vuels": {
        "settings": {"typescript": {"tsdk": "node_modules/typescript/lib/"}},
        "command": ["vue-language-server", "--stdio"],
        "languages": {"vue"},
    },
    "wgsl_analyzer": {"command": ["wgsl_analyzer"], "languages": {"wgsl"}},
    "yaml-language-server": {
        "command": ["yaml-language-server", "--stdio"],
        "languages": {"yaml", "docker-compose"},
    },
    "zls": {"command": ["zls"], "languages": {"zig"}},
    "blueprint-compiler": {
        "command": ["blueprint-compiler", "lsp"],
        "languages": {"blueprint"},
    },
    "typst-lsp": {"command": ["typst-lsp"], "languages": {"typst"}},
    "tinymist": {"command": ["tinymist"], "languages": {"typst"}},
    "pkgbuild-language-server": {
        "command": ["pkgbuild-language-server"],
        "languages": {"pkgbuild"},
    },
    "helm_ls": {"command": ["helm_ls", "serve"], "languages": {"helm"}},
    "ember-language-server": {
        "command": ["ember-language-server", "--stdio"],
        "languages": {"gts", "gjs", "glimmer"},
    },
    "ansible-language-server": {
        "command": ["ansible-language-server", "--stdio"],
        "languages": {"yaml"},
    },
    "lua-language-server": {
        "settings": {
            "Lua": {
                "hint": {
                    "enable": True,
                    "arrayIndex": "Enable",
                    "setType": True,
                    "paramName": "All",
                    "paramType": True,
                    "await": True,
                }
            }
        },
        "command": ["lua-language-server"],
        "languages": {"lua"},
    },
    "gopls": {
        "settings": {
            "hints": {
                "assignVariableTypes": True,
                "compositeLiteralFields": True,
                "constantValues": True,
                "functionTypeParameters": True,
                "parameterNames": True,
                "rangeVariableTypes": True,
            }
        },
        "command": ["gopls"],
        "languages": {"go", "gowork", "gotmpl", "gomod"},
    },
    "golangci-lint-lsp": {
        "settings": {
            "command": [
                "golangci-lint",
                "run",
                "--out-format",
                "json",
                "--issues-exit-code=1",
            ]
        },
        "command": ["golangci-lint-langserver"],
        "languages": {"go"},
    },
    "rust-analyzer": {
        "settings": {
            "inlayHints": {
                "bindingModeHints": {"enable": False},
                "closingBraceHints": {"minLines": 10},
                "closureReturnTypeHints": {"enable": "with_block"},
                "discriminantHints": {"enable": "fieldless"},
                "lifetimeElisionHints": {"enable": "skip_trivial"},
                "typeHints": {"hideClosureInitialization": False},
            }
        },
        "command": ["rust-analyzer"],
        "languages": {"rust"},
    },
    "typescript-language-server": {
        "settings": {
            "hostInfo": "helix",
            "typescript": {
                "inlayHints": {
                    "includeInlayEnumMemberValueHints": True,
                    "includeInlayFunctionLikeReturnTypeHints": True,
                    "includeInlayFunctionParameterTypeHints": True,
                    "includeInlayParameterNameHints": "all",
                    "includeInlayParameterNameHintsWhenArgumentMatchesName": True,
                    "includeInlayPropertyDeclarationTypeHints": True,
                    "includeInlayVariableTypeHints": True,
                }
            },
            "javascript": {
                "inlayHints": {
                    "includeInlayEnumMemberValueHints": True,
                    "includeInlayFunctionLikeReturnTypeHints": True,
                    "includeInlayFunctionParameterTypeHints": True,
                    "includeInlayParameterNameHints": "all",
                    "includeInlayParameterNameHintsWhenArgumentMatchesName": True,
                    "includeInlayPropertyDeclarationTypeHints": True,
                    "includeInlayVariableTypeHints": True,
                }
            },
        },
        "command": ["typescript-language-server", "--stdio"],
        "languages": {"jsx", "typescript", "javascript", "tsx"},
    },
    "svelteserver": {
        "settings": {
            "configuration": {
                "typescript": {
                    "inlayHints": {
                        "parameterTypes": {"enabled": True},
                        "variableTypes": {"enabled": True},
                        "propertyDeclarationTypes": {"enabled": True},
                        "functionLikeReturnTypes": {"enabled": True},
                        "enumMemberValues": {"enabled": True},
                        "parameterNames": {"enabled": "all"},
                    }
                },
                "javascript": {
                    "inlayHints": {
                        "parameterTypes": {"enabled": True},
                        "variableTypes": {"enabled": True},
                        "propertyDeclarationTypes": {"enabled": True},
                        "functionLikeReturnTypes": {"enabled": True},
                        "enumMemberValues": {"enabled": True},
                        "parameterNames": {"enabled": "all"},
                    }
                },
            }
        },
        "command": ["svelteserver", "--stdio"],
        "languages": {"svelte"},
    },
    "vscode-eslint-language-server": {
        "settings": {
            "validate": "on",
            "experimental": {"useFlatConfig": False},
            "rulesCustomizations": [],
            "run": "onType",
            "problems": {"shortenToSingleLine": False},
            "nodePath": "",
            "codeAction": {
                "disableRuleComment": {"enable": True, "location": "separateLine"},
                "showDocumentation": {"enable": True},
            },
            "workingDirectory": {"mode": "location"},
        },
        "command": ["vscode-eslint-language-server", "--stdio"],
        "languages": {"gts", "gjs"},
    },
}
