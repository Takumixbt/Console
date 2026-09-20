"""Standalone dino entry: ``console-dino`` / ``python -m console_dino``."""

from __future__ import annotations

import sys

from ...cli import main as console_main


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in {"dino", "console"}:
        argv = argv[1:]
    return console_main(["dino", *argv], prog="console-dino")
