"""Shared Console state file (``~/.hermes/console.state``).

Hooks write ``task_done`` / ``busy`` only. The TUI reads those flags and
stores a paused dino snapshot so ``/console`` can resume the same run.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

SCHEMA = 1
STATE_NAME = "console.state"


def hermes_home() -> Path:
    override = os.environ.get("HERMES_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".hermes"


def state_path() -> Path:
    override = os.environ.get("CONSOLE_STATE")
    if override:
        return Path(override).expanduser()
    return hermes_home() / STATE_NAME


def default_state() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "task_done": False,
        "busy": False,
        "session_id": None,
        "high_score": 0,
        "paused": None,
        "wipe_on_escape": False,
    }


def load_state() -> dict[str, Any]:
    path = state_path()
    if not path.is_file():
        return default_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_state()
    if not isinstance(data, dict):
        return default_state()
    merged = default_state()
    merged.update(data)
    merged["schema"] = SCHEMA
    return merged


def save_state(data: dict[str, Any]) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, default=_json_default)
    fd, tmp = tempfile.mkstemp(prefix="console-", suffix=".state", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _json_default(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"Cannot serialize {type(value)!r}")


def update_flags(
    *,
    task_done: bool | None = None,
    busy: bool | None = None,
    session_id: str | None = None,
    wipe_on_escape: bool | None = None,
) -> dict[str, Any]:
    """Hook-safe: flip lifecycle flags without touching the paused game."""
    data = load_state()
    if task_done is not None:
        data["task_done"] = bool(task_done)
        if task_done:
            data["wipe_on_escape"] = True
            data["busy"] = False
    if busy is not None:
        data["busy"] = bool(busy)
        if busy:
            data["task_done"] = False
            data["wipe_on_escape"] = False
    if session_id is not None:
        data["session_id"] = session_id
    if wipe_on_escape is not None:
        data["wipe_on_escape"] = bool(wipe_on_escape)
    save_state(data)
    return data


def save_paused(game_name: str, snapshot: dict[str, Any], *, wipe_on_escape: bool) -> None:
    data = load_state()
    high = max(int(data.get("high_score") or 0), int(snapshot.get("high_score") or 0))
    data["high_score"] = high
    data["paused"] = {"game": game_name, "snapshot": snapshot}
    data["wipe_on_escape"] = wipe_on_escape
    save_state(data)


def clear_paused() -> None:
    data = load_state()
    data["paused"] = None
    data["wipe_on_escape"] = False
    data["task_done"] = False
    save_state(data)


def paused_snapshot(game_name: str) -> dict[str, Any] | None:
    data = load_state()
    paused = data.get("paused")
    if not isinstance(paused, dict):
        return None
    if paused.get("game") != game_name:
        return None
    snap = paused.get("snapshot")
    return snap if isinstance(snap, dict) else None
