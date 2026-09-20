"""Game catalog. Kept import-light so game modules can register without cycles."""

from __future__ import annotations

from typing import Callable, Type

from .games.base import Game

GameFactory = Callable[[], Game]

GAMES: dict[str, GameFactory] = {}
DEFAULT_GAME = "dino"


def register(name: str) -> Callable[[Type[Game]], Type[Game]]:
    """Class decorator that publishes a game under ``/console <name>``."""

    def wrapper(cls: Type[Game]) -> Type[Game]:
        GAMES[name] = cls
        return cls

    return wrapper
