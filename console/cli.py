"""Standalone Console CLI: ``console`` / ``python -m console``."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .catalog import DEFAULT_GAME


def main(argv: list[str] | None = None, prog: str = "console") -> int:
    from .registry import GAMES, get_game  # imports the built-in games

    parser = argparse.ArgumentParser(prog=prog, description="Play Chrome's dino game (and more) in your terminal.")
    parser.add_argument("game", nargs="?", default=DEFAULT_GAME, help=f"which game (default: {DEFAULT_GAME})")
    parser.add_argument("--list", action="store_true", help="list the available games")
    parser.add_argument("--demo", action="store_true", help="let the game play itself (dino only)")
    parser.add_argument("--debug", action="store_true", help="show fps and encode time under the picture")
    parser.add_argument("--version", action="version", version=f"console {__version__}")
    args = parser.parse_args(argv)

    if args.list:
        for name in sorted(GAMES):
            print(name)
        return 0
    if args.debug:
        import os

        os.environ["CONSOLE_DEBUG"] = "1"
    try:
        if args.demo:
            from .games.dino.demo import DemoDino

            game = DemoDino.create()
        else:
            game = get_game(args.game)
    except KeyError as exc:
        print(exc.args[0], file=sys.stderr)
        return 2

    from .runner import play

    message = play(game)
    if message and message != "Left Console.":
        print(message)
    return 0
