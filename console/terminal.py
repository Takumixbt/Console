"""Raw TTY + alternate screen. Stdlib only (termios / tty / ANSI)."""

from __future__ import annotations

import os
import select
import shutil
import signal
import sys
import time
from dataclasses import dataclass
from types import FrameType, TracebackType
from typing import Callable, TextIO

# Inferred key-up after this much silence (covers typical keyboard delay).
HOLD_TIMEOUT_S = 0.09
ESC_WAIT_S = 0.05


@dataclass
class Size:
    cols: int
    rows: int


def is_tty(stream: TextIO | None = None) -> bool:
    stream = stream or sys.stdin
    try:
        return bool(stream.isatty()) and bool(sys.stdout.isatty())
    except Exception:
        return False


def terminal_size() -> Size:
    size = shutil.get_terminal_size(fallback=(80, 24))
    return Size(max(40, size.columns), max(12, size.lines))


class RawTerminal:
    """Enter alternate screen + cbreak, restore on exit."""

    def __init__(self, incoming: TextIO | None = None, outgoing: TextIO | None = None) -> None:
        self.incoming = incoming or sys.stdin
        self.outgoing = outgoing or sys.stdout
        self._fd = self.incoming.fileno()
        self._old = None
        self._prev_winch: Callable[[int, FrameType | None], None] | int | None = None
        self.resized = False
        self._held: dict[str, float] = {}

    def __enter__(self) -> RawTerminal:
        self._setup()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._restore()

    def _setup(self) -> None:
        try:
            import termios
            import tty

            self._old = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
        except Exception:
            self._old = None
        self.write("\x1b[?1049h\x1b[?25l\x1b[2J\x1b[H")
        try:
            self._prev_winch = signal.getsignal(signal.SIGWINCH)
            signal.signal(signal.SIGWINCH, self._on_winch)
        except (AttributeError, ValueError):
            self._prev_winch = None

    def _on_winch(self, _signum: int, _frame: FrameType | None) -> None:
        self.resized = True

    def _restore(self) -> None:
        if self._prev_winch is not None:
            try:
                signal.signal(signal.SIGWINCH, self._prev_winch)
            except (AttributeError, ValueError):
                pass
        self.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        if self._old is not None:
            try:
                import termios

                termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)
            except Exception:
                pass

    def write(self, text: str) -> None:
        try:
            self.outgoing.write(text)
            self.outgoing.flush()
        except BrokenPipeError:
            pass

    def paint(self, lines: list[str], inverted: bool = False) -> None:
        size = terminal_size()
        body = "\r\n".join(line[: size.cols].ljust(size.cols) for line in lines[: size.rows])
        invert = "\x1b[7m" if inverted else ""
        reset = "\x1b[0m"
        self.write(f"\x1b[H{invert}{body}{reset}")

    def poll_keys(self) -> list[tuple[str, bool]]:
        """Return ``(name, pressed)`` events, including inferred releases."""
        now = time.monotonic()
        events: list[tuple[str, bool]] = []
        raw = self._read_available()
        names = _decode_keys(raw)
        for name in names:
            if name == "esc":
                events.append(("esc", True))
                continue
            if name in {"space", "up", "down"}:
                if name not in self._held:
                    events.append((name, True))
                self._held[name] = now
            else:
                events.append((name, True))
        expired = [key for key, seen in self._held.items() if now - seen > HOLD_TIMEOUT_S]
        for key in expired:
            events.append((key, False))
            del self._held[key]
        return events

    def _read_available(self) -> bytes:
        chunks = bytearray()
        try:
            ready, _, _ = select.select([self.incoming], [], [], 0)
        except (ValueError, OSError):
            return b""
        if not ready:
            return b""
        try:
            piece = os.read(self._fd, 64)
        except OSError:
            return b""
        if not piece:
            return b""
        chunks.extend(piece)
        # Drain a possible ESC sequence.
        if piece.startswith(b"\x1b"):
            deadline = time.monotonic() + ESC_WAIT_S
            while time.monotonic() < deadline:
                try:
                    more, _, _ = select.select([self.incoming], [], [], 0.01)
                except (ValueError, OSError):
                    break
                if not more:
                    continue
                try:
                    extra = os.read(self._fd, 64)
                except OSError:
                    break
                if not extra:
                    break
                chunks.extend(extra)
        return bytes(chunks)


def _decode_keys(data: bytes) -> list[str]:
    if not data:
        return []
    names: list[str] = []
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        if b == 0x1B:
            rest = data[i:]
            if rest in {b"\x1b", b"\x1b\x1b"} or len(rest) == 1:
                names.append("esc")
                break
            if rest.startswith(b"\x1b[A") or rest.startswith(b"\x1bOA"):
                names.append("up")
                i += 3
                continue
            if rest.startswith(b"\x1b[B") or rest.startswith(b"\x1bOB"):
                names.append("down")
                i += 3
                continue
            if rest.startswith(b"\x1b[C") or rest.startswith(b"\x1bOC"):
                names.append("right")
                i += 3
                continue
            if rest.startswith(b"\x1b[D") or rest.startswith(b"\x1bOD"):
                names.append("left")
                i += 3
                continue
            names.append("esc")
            break
        if b in {ord(" "), 0x00}:
            names.append("space")
        elif b in {ord("\r"), ord("\n")}:
            names.append("space")
        i += 1
    return names
