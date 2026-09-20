"""Own the TTY, run a registered game, pause/resume via the state file."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .games.base import GameFlags, KeyEvent
from .registry import DEFAULT_GAME, get_game
from . import state as store
from .terminal import HOLD_TIMEOUT_S, RawTerminal, is_tty, terminal_size
from .games.dino.constants import MS_PER_FRAME

CLI_ONLY = (
    "Console is CLI/TUI only — it needs a real terminal. "
    "Open Hermes in a terminal and type /console."
)


@dataclass
class RunResult:
    message: str
    exit_reason: str


def parse_game_name(raw_args: str | None) -> str:
    text = (raw_args or "").strip()
    if not text or text in {"-", "--"}:
        return DEFAULT_GAME
    first = text.split()[0].lower().lstrip("/")
    if first in {"help", "-h", "--help"}:
        return "help"
    return first


def run_console(
    raw_args: str = "",
    *,
    resume: bool = True,
    require_tty: bool = True,
) -> RunResult:
    if require_tty and not is_tty():
        return RunResult(CLI_ONLY, "not-tty")

    name = parse_game_name(raw_args)
    if name == "help":
        from .registry import GAMES

        games = ", ".join(sorted(GAMES))
        return RunResult(
            f"Console games: {games}. Default is {DEFAULT_GAME}. Usage: /console [game]",
            "help",
        )

    try:
        game = get_game(name)
    except KeyError as exc:
        return RunResult(str(exc), "unknown-game")

    data = store.load_state()
    if resume:
        snap = store.paused_snapshot(game.name)
        if snap:
            game.load_snapshot(snap)
            if data.get("high_score"):
                game.high_score = max(getattr(game, "high_score", 0), int(data["high_score"]))

    flags = GameFlags(task_done=bool(data.get("task_done")), busy=bool(data.get("busy")))
    if flags.task_done:
        game.update(0, flags)

    with RawTerminal() as term:
        last = time.monotonic()
        state_mtime = _mtime()
        while True:
            now = time.monotonic()
            dt_ms = min(50.0, max(0.0, (now - last) * 1000.0))
            last = now

            for key_name, pressed in term.poll_keys():
                if key_name == "esc" and pressed:
                    return _leave(game, flags)
                game.handle_key(KeyEvent(key_name, pressed))

            mtime = _mtime()
            if mtime != state_mtime:
                state_mtime = mtime
                fresh = store.load_state()
                flags.task_done = bool(fresh.get("task_done"))
                flags.busy = bool(fresh.get("busy"))

            game.update(dt_ms, flags)
            size = terminal_size()
            lines = game.render(size.cols, size.rows)
            inverted = bool(getattr(game, "_inverted", False))
            term.paint(lines, inverted=inverted)

            elapsed = time.monotonic() - now
            sleep_for = (MS_PER_FRAME / 1000.0) - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)


def _leave(game: Any, flags: GameFlags) -> RunResult:
    wipe = bool(game.saw_task_done_banner() or flags.task_done)
    if wipe:
        store.clear_paused()
        high = int(getattr(game, "high_score", 0) or 0)
        data = store.load_state()
        data["high_score"] = max(int(data.get("high_score") or 0), high)
        store.save_state(data)
        return RunResult("Closed Console.", "wipe")

    snap = game.snapshot()
    store.save_paused(game.name, snap, wipe_on_escape=False)
    if flags.busy:
        return RunResult("Paused Console. Type /console to resume the same run.", "pause")
    return RunResult("Left Console. Type /console to resume.", "pause")


def _mtime() -> float:
    path = store.state_path()
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def run_headless(
    *,
    game_name: str = DEFAULT_GAME,
    frames: int = 120,
    script: list[tuple[int, str]] | None = None,
    cols: int = 80,
    rows: int = 24,
    dt_ms: float = MS_PER_FRAME,
    seed: int | None = 1,
    flags: GameFlags | None = None,
) -> Any:
    """Deterministic loop for tests. ``script`` is ``(frame, key)`` presses."""
    game = get_game(game_name)
    if seed is not None and hasattr(game, "rng"):
        import random

        game.rng = random.Random(seed)
        game.reset()
    flags = flags or GameFlags()
    planned: dict[int, list[str]] = {}
    for frame, key in script or []:
        planned.setdefault(frame, []).append(key)
    held: dict[str, int] = {}
    hold_frames = max(1, int(HOLD_TIMEOUT_S * 1000 / dt_ms))
    for i in range(frames):
        for key in planned.get(i, []):
            game.handle_key(KeyEvent(key, True))
            held[key] = i
        expired = [key for key, seen in held.items() if i - seen >= hold_frames]
        for key in expired:
            game.handle_key(KeyEvent(key, False))
            del held[key]
        game.update(dt_ms, flags)
        game.render(cols, rows)
    return game
