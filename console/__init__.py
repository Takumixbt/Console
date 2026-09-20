"""Console — a small multi-game terminal for Hermes (and standalone play)."""

from .registry import GAMES, default_game, get_game

__version__ = "1.0.0"
__all__ = ["GAMES", "default_game", "get_game", "__version__"]
