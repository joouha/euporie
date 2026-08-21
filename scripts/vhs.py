#!/usr/bin/env python3
"""Run a VHS-style .tape script against wezterm, capturing screenshots with KWin.

Target platform: Linux + Wayland (KWin/Plasma for screenshots). Wezterm must
already be running as a GUI process so ``wezterm cli`` can connect to it.

Supported VHS commands (case-insensitive)::

    # comment
    Output <path>                 png/webm; multiple frames -> webm
    Set FontSize <n>
    Set Cols <n>                  window width in character cells
    Set Rows <n>                  window height in character cells
    Set Shell <name>              shell to launch (default: $SHELL or bash)
    Set FrameRate <fps>           webm framerate (default: 10)
    Set TypingSpeed <duration>    delay between typed characters (default: 50ms)
    Type "text"                   send literal text (honours TypingSpeed)
    Type `text`                   single quotes / backticks also accepted
    Type@<time> "text"            override typing speed for this command
    Enter                         send <Return>
    Tab                           send <Tab>
    Backspace [n]                 send <BS> (n times, default 1)
    Space [n]
    Up [n] / Down [n] / Left [n] / Right [n]
    Escape
    Ctrl+<key>                    e.g. Ctrl+C, Ctrl+Space
    Alt+<key>
    Sleep <duration>              e.g. 500ms, 2s, 1.5s
    Screenshot [path]             grab a frame; path optional (auto-named)
    Hide                          stop capturing frames
    Show                          resume capturing frames
    Wait                          alias for Sleep 500ms

A frame is captured automatically after every visible command (matching VHS),
so explicit ``Screenshot`` commands are optional.

Unsupported VHS features are ignored with a warning.

Usage::

    python vhs_wezterm.py path/to/script.tape
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# .tape parser
# ---------------------------------------------------------------------------

_QUOTED = re.compile(r'^(["\'`])(.*)\1$', re.DOTALL)
_DURATION = re.compile(r"^([0-9]*\.?[0-9]+)\s*(ms|s|m)?$", re.IGNORECASE)


@dataclass
class Cmd:
    name: str
    arg: str = ""
    lineno: int = 0
    at_time: float | None = None
    scope: str = "line"


@dataclass
class TapeScript:
    output: Path | None = None
    cols: int = 80
    rows: int = 24
    font_size: int = 14
    shell: str = field(default_factory=lambda: os.environ.get("SHELL", "/bin/bash"))
    framerate: int = 10
    typing_speed: float = 0.05
    commands: list[Cmd] = field(default_factory=list)


def _strip_quotes(s: str) -> str:
    s = s.strip()
    m = _QUOTED.match(s)
    return m.group(2) if m else s


def parse_tape(path: Path, _seen: set[Path] | None = None) -> TapeScript:
    """Parse a .tape file into a :class:`TapeScript`.

    Args:
        path: The .tape file to parse.
        _seen: Set of already-parsed tape paths, used internally to guard
            against circular ``Source`` references.

    Returns:
        The parsed tape script.
    """
    path = path.resolve()
    if _seen is None:
        _seen = set()
    if path in _seen:
        _warn(f"skipping circular Source of {path}")
        return TapeScript()
    _seen.add(path)
    script = TapeScript()
    for lineno, raw in enumerate(path.read_text().splitlines(), start=1):
        # strip comments (but not inside quotes)
        line = _strip_comment(raw).strip()
        if not line:
            continue
        head, _, rest = line.partition(" ")
        head, at_time = _split_at_time(head)
        head_l = head.lower()
        rest = rest.strip()

        if head_l == "output":
            script.output = Path(_strip_quotes(rest))
        elif head_l == "set":
            key, _, value = rest.partition(" ")
            value = _strip_quotes(value)
            kl = key.lower()
            if kl == "fontsize":
                script.font_size = int(value)
            elif kl in {"cols", "width"}:
                script.cols = int(value)
            elif kl in {"rows", "height"}:
                script.rows = int(value)
            elif kl == "shell":
                script.shell = value
            elif kl == "framerate":
                script.framerate = int(value)
            elif kl == "typingspeed":
                script.typing_speed = _parse_duration(value)
            else:
                _warn(f"line {lineno}: ignoring unsupported `Set {key}`")
        elif head_l in {
            "type",
            "enter",
            "tab",
            "backspace",
            "space",
            "up",
            "down",
            "left",
            "right",
            "home",
            "end",
            "pageup",
            "pagedown",
            "delete",
            "escape",
            "sleep",
            "screenshot",
            "hide",
            "show",
        }:
            script.commands.append(Cmd(head_l, rest, lineno, at_time))
        elif head_l == "source":
            source_path = Path(_strip_quotes(rest))
            if not source_path.is_absolute():
                source_path = path.parent / source_path
            if not source_path.exists():
                _warn(f"line {lineno}: Source file not found: {source_path}")
            else:
                sourced = parse_tape(source_path, _seen)
                script.commands.extend(sourced.commands)
        elif head_l == "wait" or head_l.startswith("wait+"):
            scope = head_l.partition("+")[2] or "screen"
            script.commands.append(Cmd("wait", rest, lineno, at_time, scope=scope))
        elif (
            head_l.startswith("ctrl+")
            or head_l.startswith("alt+")
            or head_l.startswith("shift+")
        ):
            chord_line = f"{head} {rest}".strip()
            script.commands.append(Cmd("chord", chord_line, lineno, at_time))
        else:
            _warn(f"line {lineno}: ignoring unknown command `{head}`")
    return script


def _strip_comment(line: str) -> str:
    out: list[str] = []
    quote: str | None = None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"', "`"):
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out)


def _split_at_time(head: str) -> tuple[str, float | None]:
    """Split a command head like ``Type@500ms`` into name and seconds."""
    name, sep, t = head.partition("@")
    if not sep:
        return name, None
    return name, _parse_duration(t)


def _parse_duration(text: str) -> float:
    m = _DURATION.match(text.strip())
    if not m:
        raise ValueError(f"bad duration: {text!r}")
    n = float(m.group(1))
    unit = (m.group(2) or "s").lower()
    return n * {"ms": 1e-3, "s": 1.0, "m": 60.0}[unit]


def _warn(msg: str) -> None:
    print(f"[vhs_wezterm] warning: {msg}", file=sys.stderr)


def _info(msg: str) -> None:
    print(f"[vhs_wezterm] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# wezterm driver
# ---------------------------------------------------------------------------


class Wezterm:
    """Thin wrapper around ``wezterm cli``."""

    def __init__(self) -> None:
        if not shutil.which("wezterm"):
            raise SystemExit("wezterm not found in PATH")
        self.pane_id: int | None = None
        self.window_id: int | None = None

    def _cli(self, *args: str, capture: bool = False) -> str:
        cmd = ["wezterm", "cli", *args]
        if capture:
            return subprocess.check_output(cmd, text=True)
        subprocess.check_call(cmd)
        return ""

    def spawn(self, shell: str, *, cols: int, rows: int, font_size: int) -> int:
        """Spawn a new wezterm window running *shell*. Returns the new pane id.

        The window is sized directly in character cells via wezterm's
        ``initial_cols``/``initial_rows`` config, alongside the requested font
        size (wezterm's ``--config`` flag accepts ``KEY=VALUE`` Lua snippets).
        """
        # spawn a brand new window. The output is the new pane id (integer).
        out = subprocess.check_output(
            [
                "wezterm",
                "--config",
                f"font_size={font_size}",
                "--config",
                f"initial_cols={cols}",
                "--config",
                f"initial_rows={rows}",
                "--config",
                "enable_tab_bar=false",
                "cli",
                "spawn",
                "--new-window",
                "--",
                shell,
            ],
            text=True,
        ).strip()
        try:
            self.pane_id = int(out.splitlines()[-1].strip())
        except (ValueError, IndexError) as exc:
            raise RuntimeError(
                f"could not parse pane id from wezterm: {out!r}"
            ) from exc

        # let wezterm settle, then look up the window id for this pane.
        time.sleep(0.4)
        self.window_id = self._lookup_window_id(self.pane_id)
        return self.pane_id

    def _lookup_window_id(self, pane_id: int) -> int | None:
        try:
            data = self._cli("list", "--format=json", capture=True)
        except subprocess.CalledProcessError:
            return None
        try:
            for entry in json.loads(data):
                if entry.get("pane_id") == pane_id:
                    return entry.get("window_id")
        except json.JSONDecodeError:
            pass
        return None

    def send_text(self, text: str) -> None:
        if self.pane_id is None:
            raise RuntimeError("no pane spawned")
        # --no-paste so each char is delivered individually; otherwise wezterm
        # uses bracketed paste which most TUIs will not interpret as keystrokes.
        # Pass the text via stdin rather than as an argv entry, since argv
        # cannot contain embedded NUL bytes (e.g. for Ctrl+Space => "\x00").
        subprocess.run(
            [
                "wezterm",
                "cli",
                "send-text",
                "--pane-id",
                str(self.pane_id),
                "--no-paste",
            ],
            input=text.encode("utf-8"),
            check=True,
        )

    def get_text(self, *, scope: str = "screen") -> str:
        """Return the current pane text.

        Args:
            scope: ``"line"`` returns only the last non-empty line, anything
                else returns the whole visible screen.

        Returns:
            The captured pane text.
        """
        if self.pane_id is None:
            raise RuntimeError("no pane spawned")
        text = self._cli("get-text", "--pane-id", str(self.pane_id), capture=True)
        if scope == "line":
            lines = text.rstrip("\n").splitlines()
            return lines[-1] if lines else ""
        return text

    def send_key(self, key: str) -> None:
        """Send a single named key. We map it to its ASCII/CSI sequence."""
        seq = _KEY_SEQUENCES.get(key.lower())
        if seq is None:
            raise ValueError(f"unknown key: {key}")
        self.send_text(seq)

    def send_chord(self, chord: str) -> None:
        """Send a chord like ``Ctrl+C`` or ``Alt+x``.

        Simple chords (Ctrl+<letter>, Alt+<char>, Shift+Tab) are sent as their
        legacy byte sequences. Modifier combinations involving named keys like
        ``Ctrl+Enter`` are sent using the kitty keyboard / CSI-u encoding
        ``CSI <codepoint> ; <modifiers> u``.
        """
        parts = [p.strip().lower() for p in chord.split("+")]
        mods, key = set(parts[:-1]), parts[-1]
        if mods == {"shift"} and key == "tab":
            self.send_text("\x1b[Z")
            return
        if mods == {"ctrl"} and len(key) == 1 and key.isalpha():
            self.send_text(chr(ord(key) - 96))
            return
        if mods == {"ctrl"} and key == "space":
            self.send_text("\x00")
            return
        if mods == {"ctrl"} and key in {"[", "escape", "esc"}:
            self.send_text("\x1b")
            return
        if mods == {"alt"} and len(key) == 1:
            self.send_text("\x1b" + key)
            return
        seq = _csi_u_sequence(mods, key)
        if seq is not None:
            self.send_text(seq)
            return
        _warn(f"unsupported chord {chord!r}; skipping")

    def activate(self) -> None:
        """Bring the wezterm window to the front so spectacle can grab it."""
        if self.pane_id is None:
            return
        try:
            self._cli("activate-pane", "--pane-id", str(self.pane_id))
        except subprocess.CalledProcessError:
            pass

    def kill_window(self) -> None:
        if self.pane_id is None:
            return
        try:
            self._cli("kill-pane", "--pane-id", str(self.pane_id))
        except subprocess.CalledProcessError:
            pass


# CSI-u codepoints for named keys (kitty keyboard protocol).
_CSI_U_KEY_CODES: dict[str, int] = {
    "enter": 13,
    "return": 13,
    "tab": 9,
    "backspace": 127,
    "escape": 27,
    "esc": 27,
    "space": 32,
}

_CSI_U_MOD_BITS: dict[str, int] = {
    "shift": 1,
    "alt": 2,
    "ctrl": 4,
    "super": 8,
}


def _csi_u_sequence(mods: set[str], key: str) -> str | None:
    """Encode a modifier+key chord as a CSI-u escape sequence.

    Returns ``None`` if the key is not recognised.
    """
    code = _CSI_U_KEY_CODES.get(key)
    if code is None:
        if len(key) == 1:
            code = ord(key)
        else:
            return None
    bits = 0
    for mod in mods:
        if mod not in _CSI_U_MOD_BITS:
            return None
        bits |= _CSI_U_MOD_BITS[mod]
    modifier = bits + 1
    return f"\x1b[{code};{modifier}u"


_KEY_SEQUENCES: dict[str, str] = {
    "enter": "\r",
    "return": "\r",
    "tab": "\t",
    "backspace": "\x7f",
    "space": " ",
    "escape": "\x1b",
    "esc": "\x1b",
    "up": "\x1b[A",
    "down": "\x1b[B",
    "right": "\x1b[C",
    "left": "\x1b[D",
    "home": "\x1b[H",
    "end": "\x1b[F",
    "pageup": "\x1b[5~",
    "pagedown": "\x1b[6~",
    "delete": "\x1b[3~",
}


# ---------------------------------------------------------------------------
# KWin screenshot
# ---------------------------------------------------------------------------


class KWinScreenshot:
    """Capture the active window via KWin's ScreenShot2 D-Bus interface.

    A pipe FD is handed to KWin, KWin writes raw image bytes into it, and the
    D-Bus reply carries the metadata needed to decode those bytes. Requires
    PyQt6 and a running Wayland KWin session.
    """

    def __init__(self) -> None:
        from PyQt6.QtDBus import QDBusConnection, QDBusInterface
        from PyQt6.QtGui import QGuiApplication

        # A QGuiApplication instance is required for QImage and the DBus
        # machinery to function. Reuse one if it already exists.
        self._app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])

        # Build the D-Bus interface once and reuse it for every capture; it is
        # relatively expensive to construct and re-resolve per frame.
        self._iface = QDBusInterface(
            "org.kde.KWin",
            "/org/kde/KWin/ScreenShot2",
            "org.kde.KWin.ScreenShot2",
            QDBusConnection.sessionBus(),
        )

        # PNG encoding is expensive, so it is pushed off the capture hot path
        # onto a background writer thread. The hot path only pays the capture
        # cost and a cheap queue put.
        self._save_queue: queue.Queue[tuple[object, Path] | None] = queue.Queue()
        self._save_error: BaseException | None = None
        self._writer = threading.Thread(target=self._writer_loop, daemon=True)
        self._writer.start()

    def _writer_loop(self) -> None:
        """Encode and write queued frames on a background thread."""
        while True:
            item = self._save_queue.get()
            if item is None:
                self._save_queue.task_done()
                break
            image, dest = item
            try:
                self._save_image(image, dest)
            except BaseException as exc:
                if self._save_error is None:
                    self._save_error = exc
            finally:
                self._save_queue.task_done()

    @staticmethod
    def _read_exact(fd: int, size: int) -> bytes:
        chunks = []
        remaining = size
        while remaining > 0:
            chunk = os.read(fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _image_from_result(self, results: dict, read_fd: int):  # type: ignore[no-untyped-def]
        from PyQt6.QtGui import QImage

        if results.get("type") != "raw":
            raise RuntimeError(f"unsupported result type: {results.get('type')}")

        width = int(results["width"])
        height = int(results["height"])
        stride = int(results["stride"])
        fmt = QImage.Format(int(results["format"]))

        data = self._read_exact(read_fd, stride * height)
        if len(data) != stride * height:
            raise RuntimeError("short read from KWin pipe")

        # No copy: ``data`` is a local ``bytes`` object that stays alive for
        # as long as the caller holds a reference to it. The caller must keep
        # the returned tuple intact until the image has been consumed.
        return QImage(data, width, height, stride, fmt), data

    def capture(self):  # type: ignore[no-untyped-def]
        """Capture the active window and return a raw ``QImage``.

        No PNG encoding or buffer copy happens here, so this measures the pure
        capture cost. The returned image shares memory with an internal
        ``bytes`` buffer that is kept alive for the lifetime of the image.

        Returns:
            The captured ``QImage`` (must be consumed/saved before being
            discarded).
        """
        from PyQt6.QtCore import QVariant
        from PyQt6.QtDBus import QDBusUnixFileDescriptor

        # include-decoration matches spectacle's previous behaviour.
        options = {
            "include-cursor": False,
            "include-decoration": True,
            "native-resolution": False,
        }

        read_fd, write_fd = os.pipe()
        try:
            reply = self._iface.call(
                "CaptureActiveWindow",
                options,
                QVariant(QDBusUnixFileDescriptor(write_fd)),
            )
            # KWin has dup'd the write end; close ours so reads see EOF.
            os.close(write_fd)
            write_fd = -1

            if reply.type() == reply.MessageType.ErrorMessage:
                raise RuntimeError(
                    f"CaptureActiveWindow failed: {reply.errorMessage()}"
                )

            args = reply.arguments()
            if not args or not isinstance(args[0], dict):
                raise RuntimeError(
                    f"CaptureActiveWindow returned unexpected reply: {args!r}"
                )

            image, buffer = self._image_from_result(args[0], read_fd)
        finally:
            if write_fd != -1:
                os.close(write_fd)
            os.close(read_fd)

        if image.isNull():
            raise RuntimeError("KWin returned a null image")
        # Stash the backing buffer on the image so it outlives this call.
        image._vhs_buffer = buffer  # type: ignore[attr-defined]
        return image

    @staticmethod
    def _save_image(image, dest: Path) -> None:  # type: ignore[no-untyped-def]
        """Encode and write a captured ``QImage`` to *dest* as PNG."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest.unlink()
        if not image.save(str(dest), "PNG"):
            raise RuntimeError(f"failed to save screenshot: {dest}")

    # Backwards-compatible synchronous alias.
    save = _save_image

    def save_async(self, image, dest: Path) -> None:  # type: ignore[no-untyped-def]
        """Queue a captured ``QImage`` to be encoded/saved off the hot path.

        The image's backing buffer is kept alive by the image object itself,
        so it remains valid until the writer thread consumes it.
        """
        if self._save_error is not None:
            raise self._save_error
        self._save_queue.put((image, dest))

    def grab_active(self, dest: Path) -> None:
        image = self.capture()
        self._save_image(image, dest)

    def close(self) -> None:
        """Flush any pending writes and stop the writer thread."""
        self._save_queue.put(None)
        self._writer.join()
        if self._save_error is not None:
            raise self._save_error


# ---------------------------------------------------------------------------
# webm assembly
# ---------------------------------------------------------------------------


def frames_to_webm(
    frames: list[Path],
    dest: Path,
    framerate: int,
    durations: list[float] | None = None,
    *,
    fixed_framerate: bool = False,
) -> None:
    """Assemble PNG frames into a lossless VP9 webm using ffmpeg.

    Args:
        frames: The PNG frames to assemble, in order.
        dest: The output webm path.
        framerate: The output framerate.
        durations: Optional per-frame display durations in seconds. When
            omitted, each frame is shown for ``1 / framerate`` seconds.
        fixed_framerate: When ``True``, encode a constant frame rate output
            (resampling to *framerate*) while still honouring the per-frame
            display durations.
    """
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not found in PATH")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        list_file = Path(f.name)
        for i, frame in enumerate(frames):
            # Always honour the calculated per-frame durations; in fixed mode
            # ffmpeg resamples these to a constant output frame rate below.
            if durations is not None and i < len(durations):
                duration = durations[i]
            else:
                duration = 1.0 / framerate
            f.write(f"file {shlex.quote(str(frame.resolve()))}\n")
            f.write(f"duration {duration:.4f}\n")
        # ffmpeg concat demuxer needs the last file repeated without a duration
        f.write(f"file {shlex.quote(str(frames[-1].resolve()))}\n")
    # With a fixed frame rate we resample to a constant output rate while still
    # respecting the per-frame display durations; otherwise we pass the frame
    # timing through unchanged for a variable rate.
    rate_args = (
        ["-fps_mode", "cfr", "-r", str(framerate)]
        if fixed_framerate
        else ["-fps_mode", "passthrough"]
    )
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c:v",
                "libvpx-vp9",
                "-lossless",
                "1",
                "-pix_fmt",
                "yuva420p",
                *rate_args,
                str(dest),
            ],
            check=True,
        )
    finally:
        list_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------


# Time to wait after sending a keystroke before grabbing a frame, so the
# terminal application has redrawn in response to the input.
_REDRAW_SETTLE = 0.2

# Maximum time a `Wait` command polls for its regex before giving up.
_WAIT_TIMEOUT = 15.0


@dataclass
class _State:
    capturing: bool = True
    captured_in_command: bool = False
    captured_in_previous: bool = False


def _expand_count(arg: str) -> int:
    return int(arg) if arg.strip() else 1


def _capture(
    wez: Wezterm,
    spec: KWinScreenshot,
    frame_dir: Path,
    frames: list[Path],
    durations: list[float],
    script: TapeScript,
    dest: Path | None = None,
) -> None:
    """Grab a frame and append it to the frame list."""
    if dest is None:
        dest = frame_dir / f"frame-{len(frames):04d}.png"
    image = spec.capture()
    spec.save_async(image, dest)
    frames.append(dest)
    durations.append(1.0 / script.framerate)
    _info(f"captured frame {len(frames)}: {dest}")


def _screenshot(
    spec: KWinScreenshot,
    frame_dir: Path,
    frames: list[Path],
    dest: Path | None = None,
) -> None:
    """Capture a standalone PNG screenshot without adding it to the webm frames."""
    if dest is None:
        dest = frame_dir / f"screenshot-{len(frames):04d}.png"
    image = spec.capture()
    spec.save_async(image, dest)
    _info(f"captured screenshot: {dest}")


def run(
    script: TapeScript,
    *,
    keep_frames: bool = False,
    fixed_framerate: bool = False,
) -> Path | None:
    wez = Wezterm()
    spec = KWinScreenshot()

    pane = wez.spawn(
        script.shell,
        cols=script.cols,
        rows=script.rows,
        font_size=script.font_size,
    )
    _info(f"spawned wezterm pane {pane}")
    # Give the shell a moment to draw its prompt.
    time.sleep(0.6)
    # Activate the window once; it keeps focus for the duration of the run, so
    # there is no need to re-activate before every frame.
    wez.activate()
    time.sleep(0.1)

    frame_dir = Path(tempfile.mkdtemp(prefix="vhs_wezterm_"))
    frames: list[Path] = []
    durations: list[float] = []
    state = _State()
    try:
        for cmd in script.commands:
            state.captured_in_command = False
            _dispatch(cmd, wez, spec, frame_dir, frames, durations, script, state)
            # Auto-capture a frame after each visible command (VHS behaviour).
            # `screenshot` captures explicitly and `type` may capture per
            # character; control commands do not capture at all.
            if (
                state.capturing
                and not state.captured_in_command
                and cmd.name not in {"screenshot", "hide", "sleep", "wait"}
            ):
                # Let the application redraw in response to the command before
                # grabbing the frame, otherwise we capture the stale screen and
                # any following `Sleep` extends the wrong frame.
                time.sleep(_REDRAW_SETTLE)
                _capture(wez, spec, frame_dir, frames, durations, script)
                state.captured_in_command = True
            state.captured_in_previous = state.captured_in_command
    finally:
        wez.kill_window()
        spec.close()

    return _finalise(
        script,
        frames,
        durations,
        frame_dir,
        keep_frames=keep_frames,
        fixed_framerate=fixed_framerate,
    )


def _dispatch(
    cmd: Cmd,
    wez: Wezterm,
    spec: KWinScreenshot,
    frame_dir: Path,
    frames: list[Path],
    durations: list[float],
    script: TapeScript,
    state: _State,
) -> None:
    name, arg = cmd.name, cmd.arg
    if name == "type":
        delay = cmd.at_time if cmd.at_time is not None else script.typing_speed
        text = _strip_quotes(arg)
        if delay <= 0:
            # Send the whole string in one go: this is essential for things
            # like mouse-event escape sequences which must arrive as a single
            # unit, and also avoids redundant per-character round-trips.
            wez.send_text(text)
        else:
            for ch in text:
                wez.send_text(ch)
                time.sleep(delay)
                # Capture a frame after each character so the typing is
                # animated in the output (matching VHS behaviour).
                if state.capturing:
                    _capture(wez, spec, frame_dir, frames, durations, script)
                    state.captured_in_command = True
    elif name in {
        "enter",
        "tab",
        "backspace",
        "space",
        "up",
        "down",
        "left",
        "right",
        "home",
        "end",
        "pageup",
        "pagedown",
        "delete",
    }:
        count = _expand_count(arg)
        delay = cmd.at_time or 0.0
        for i in range(count):
            wez.send_key(name)
            # For repeated key presses, capture a frame after each press so
            # the repetition is animated in the output (matching the way
            # `Type` captures per character).
            if count > 1 and state.capturing:
                time.sleep(_REDRAW_SETTLE)
                _capture(wez, spec, frame_dir, frames, durations, script)
                state.captured_in_command = True
            if delay > 0 and i < count - 1:
                time.sleep(delay)
    elif name == "escape":
        wez.send_key("escape")
    elif name == "sleep":
        seconds = _parse_duration(arg)
        # If nothing was captured for the previous command (e.g. a `Wait`
        # that matched immediately with an unchanged screen), grab a fresh
        # frame so this sleep extends the *current* state, not the stale
        # frame that preceded the wait.
        if state.capturing and frames and not state.captured_in_previous:
            _capture(wez, spec, frame_dir, frames, durations, script)
            state.captured_in_command = True
        if durations:
            durations[-1] += seconds
        time.sleep(seconds)
    elif name == "wait":
        pattern = re.compile(_strip_quotes(arg).strip().strip("/") or r">$")
        interval = cmd.at_time or (1.0 / script.framerate)
        deadline = time.monotonic() + _WAIT_TIMEOUT
        previous_text: str | None = None
        # Time accumulated against the most recent frame while the screen
        # has not changed, so unchanged intervals extend that frame instead
        # of producing duplicate captures.
        idle_time = 0.0
        while time.monotonic() < deadline:
            text = wez.get_text(scope=cmd.scope)
            if pattern.search(text):
                break
            if state.capturing and text != previous_text:
                if idle_time and durations:
                    durations[-1] += idle_time
                    idle_time = 0.0
                _capture(wez, spec, frame_dir, frames, durations, script)
                state.captured_in_command = True
                previous_text = text
            else:
                idle_time += interval
            time.sleep(interval)
        else:
            _warn(f"Wait timed out after {_WAIT_TIMEOUT}s (line {cmd.lineno})")
        # Flush any trailing idle time onto the last captured frame so
        # playback timing reflects the full wait duration.
        if idle_time and durations:
            durations[-1] += idle_time
        # Capture a final frame reflecting the matched (or timed-out) state,
        # but only if it actually differs from the last captured frame --
        # otherwise we'd produce a duplicate that a following `Sleep` would
        # extend, making it look like the pre-Wait frame is being held.
        final_text = wez.get_text(scope=cmd.scope)
        if state.capturing and final_text != previous_text:
            _capture(wez, spec, frame_dir, frames, durations, script)
            state.captured_in_command = True
    elif name == "chord":
        wez.send_chord(arg)
    elif name == "screenshot":
        path = _strip_quotes(arg) if arg.strip() else ""
        dest: Path | None = None
        if path:
            dest = Path(path)
            if not dest.is_absolute():
                # resolve relative to the output folder so screenshots land
                # alongside the tape's configured Output.
                if script.output is not None:
                    dest = script.output.parent / dest
                else:
                    dest = Path.cwd() / dest
        _screenshot(spec, frame_dir, frames, dest)
    elif name == "hide":
        state.capturing = False
    elif name == "show":
        state.capturing = True
        # Give the application time to finish redrawing (e.g. dismissing the
        # `:` command prompt) before the next capturing command grabs a frame,
        # otherwise we capture the stale command line still on screen.
        time.sleep(_REDRAW_SETTLE)
    else:
        _warn(f"unhandled command `{name}` (line {cmd.lineno})")


def _finalise(
    script: TapeScript,
    frames: list[Path],
    durations: list[float],
    frame_dir: Path,
    *,
    keep_frames: bool,
    fixed_framerate: bool = False,
) -> Path | None:
    out = script.output
    if not frames:
        _warn("No frames captured; nothing to write")
        if not keep_frames:
            shutil.rmtree(frame_dir, ignore_errors=True)
        return None

    if out is None:
        if not keep_frames:
            _info(f"frames left in {frame_dir}")
        return frame_dir

    out = out.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    if len(frames) == 1 and out.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        shutil.copy(frames[0], out)
        _info(f"wrote {out}")
    elif out.suffix.lower() == ".webm" or len(frames) > 1:
        target = out if out.suffix.lower() == ".webm" else out.with_suffix(".webm")
        frames_to_webm(
            frames,
            target,
            script.framerate,
            durations,
            fixed_framerate=fixed_framerate,
        )
        _info(f"wrote {target}")
        out = target
    else:
        # multi-frame but Output is a single image -- save the last frame.
        shutil.copy(frames[-1], out)
        _info(f"wrote {out} (last of {len(frames)} frames)")

    if not keep_frames:
        shutil.rmtree(frame_dir, ignore_errors=True)
    return out


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def _resolve_output(
    tape_path: Path, script_output: Path | None, cli_output: Path | None
) -> Path:
    """Resolve the final output path.

    Priority: ``--output`` flag, then the tape's ``Output`` directive, then a
    default derived from *tape_path*. If the chosen path refers to an existing
    directory (or ends in a separator), the tape's stem with a ``.webm``
    extension is appended.
    """
    default_ext = ".webm"
    if cli_output is not None:
        candidate = cli_output.expanduser()
        looks_like_dir = str(cli_output).endswith(("/", os.sep)) or (
            candidate.exists() and candidate.is_dir()
        )
        if looks_like_dir:
            return candidate / (tape_path.stem + default_ext)
        return candidate
    if script_output is not None:
        return script_output
    return tape_path.with_suffix(default_ext)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tape", type=Path, help="path to .tape script")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help=(
            "output path; if a directory, the tape file name (with a .webm "
            "extension) is used inside it. Overrides any `Output` directive "
            "in the .tape file."
        ),
    )
    parser.add_argument(
        "--keep-frames",
        action="store_true",
        help="do not delete intermediate PNG frames after assembly",
    )
    parser.add_argument(
        "--fixed-framerate",
        action="store_true",
        help=(
            "encode a fixed (constant) frame rate output instead of the default "
            "variable frame rate; per-frame display durations are preserved and "
            "resampled to the configured FrameRate"
        ),
    )
    args = parser.parse_args(argv)

    script = parse_tape(args.tape)
    script.output = _resolve_output(args.tape, script.output, args.output)
    _info(f"output will be written to {script.output}")
    result = run(
        script,
        keep_frames=args.keep_frames,
        fixed_framerate=args.fixed_framerate,
    )
    return 0 if result is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
