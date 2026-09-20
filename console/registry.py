"""Resolve Console games. Importing this module loads built-in games."""

from __future__ import annotations

from .catalog import DEFAULT_GAME, GAMES, register
from .games.base import Game

# Built-in games self-register on import.
from .games.dino.game import DinoGame  # noqa: F401

__all__ = ["DEFAULT_GAME", "GAMES", "DinoGame", "default_game", "get_game", "register"]


def get_game(name: str | None = None) -> Game:
    key = (name or DEFAULT_GAME).strip().lower() or DEFAULT_GAME
    if key not in GAMES:
        known = ", ".join(sorted(GAMES)) or "(none loaded)"
        raise KeyError(f"Unknown game {key!r}. Available: {known}")
    return GAMES[key]()


def default_game() -> Game:
    return get_game(DEFAULT_GAME)
