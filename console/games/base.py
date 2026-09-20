"""Shared game protocol for Console."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class GameFlags:
    """Sidecar flags from Hermes / the state file. Never drive physics."""

    task_done: bool = False
    busy: bool = False


@dataclass
class KeyEvent:
    """Normalized input. ``pressed`` is False on inferred key-up."""

    name: str
    pressed: bool = True


class Game(Protocol):
    name: str

    def reset(self) -> None: ...
    def snapshot(self) -> dict[str, Any]: ...
    def load_snapshot(self, data: dict[str, Any]) -> None: ...
    def handle_key(self, event: KeyEvent) -> None: ...
    def update(self, dt_ms: float, flags: GameFlags) -> None: ...
    def render(self, cols: int, rows: int) -> list[str]: ...
    def saw_task_done_banner(self) -> bool: ...


@dataclass
class BaseGame:
    """Optional helper with default snapshot plumbing."""

    name: str = "game"
    _saw_banner: bool = field(default=False, init=False)

    def saw_task_done_banner(self) -> bool:
        return self._saw_banner
