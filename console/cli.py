"""Standalone Console CLI: ``console`` / ``python -m console``."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .registry import DEFAULT_GAME, GAMES
from .runner import run_console, run_headless


def build_parser(prog: str = "console") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Console — Chrome dino (and later games) in the terminal.",
    )
    parser.add_argument(
        "game",
        nargs="?",
        default=DEFAULT_GAME,
        help=f"Game to play (default: {DEFAULT_GAME}). Available: {', '.join(sorted(GAMES))}",
    )
    parser.add_argument("--version", action="version", version=f"Console {__version__}")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without a TTY (for tests). Prints score and crash flag.",
    )
    parser.add_argument("--frames", type=int, default=180, help="Headless frame count.")
    parser.add_argument("--seed", type=int, default=1, help="Headless RNG seed.")
    parser.add_argument(
        "--script",
        default="",
        help="Headless key script: jump@40,duck@80 (frame@key).",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Do not resume a paused run from ~/.hermes/console.state.",
    )
    return parser


def _parse_script(text: str) -> list[tuple[int, str]]:
    events: list[tuple[int, str]] = []
    aliases = {"jump": "space", "space": "space", "up": "up", "duck": "down", "down": "down"}
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "@" not in part:
            raise SystemExit(f"Bad --script item {part!r}. Use key@frame (e.g. jump@40).")
        key, _, frame = part.partition("@")
        if key.isdigit() and not frame.isdigit():
            frame, key = key, frame
        events.append((int(frame), aliases.get(key, key)))
    return events


def main(argv: list[str] | None = None, *, prog: str = "console") -> int:
    parser = build_parser(prog)
    args = parser.parse_args(argv)
    if args.headless:
        game = run_headless(
            game_name=args.game,
            frames=args.frames,
            script=_parse_script(args.script),
            seed=args.seed,
        )
        score = game.score() if hasattr(game, "score") else 0
        crashed = bool(getattr(game, "crashed", False))
        print(f"score={score} crashed={int(crashed)} game={game.name}")
        return 0

    result = run_console(args.game, resume=not args.fresh, require_tty=True)
    if result.exit_reason == "not-tty":
        print(result.message, file=sys.stderr)
        return 2
    if result.message:
        print(result.message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
