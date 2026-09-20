"""Hermes Agent plugin: ``/console`` plus lifecycle flags for the TASK DONE banner.

Hooks only write ``~/.hermes/console.state``. They never move the dino or
spawn cacti. Gameplay is idle with respect to tool calls.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from . import state as store
from .runner import CLI_ONLY, run_console
from .terminal import is_tty

# Slash-command names that usually start a long agent run.
_START_COMMANDS = {
    "goal",
    "retry",
    "continue",
    "plan",
}

# Official Hermes hooks we observe. ``agent_loop_stopped`` is registered too
# for forward compatibility — current Hermes warns and still stores unknown
# hook names, but does not fire this one yet.
_HOOKS = (
    "on_session_start",
    "on_session_end",
    "pre_command",
    "subagent_stop",
    "agent_loop_stopped",
)


def _looks_like_gateway() -> bool:
    if os.environ.get("HERMES_GATEWAY"):
        return True
    platform = (os.environ.get("HERMES_PLATFORM") or os.environ.get("HERMES_CHANNEL") or "").lower()
    if platform in {"telegram", "discord", "slack", "whatsapp", "irc", "sms", "signal", "gateway"}:
        return True
    return False


def handle_console(raw_args: str = "") -> str:
    """Slash-command handler. Blocks on a TTY until Esc; no-op on gateways."""
    if _looks_like_gateway() or not is_tty():
        return CLI_ONLY
    result = run_console(raw_args or "", resume=True, require_tty=True)
    return result.message


def _on_session_start(session_id: str = "", **_kwargs) -> None:
    store.update_flags(busy=True, task_done=False, session_id=session_id or None)


def _on_session_end(
    session_id: str = "",
    completed: bool = False,
    interrupted: bool = False,
    **_kwargs,
) -> None:
    # Best-effort "goal done": Hermes has no dedicated /goal-finished hook.
    # A completed conversation is the closest signal. Interrupted runs stay
    # busy=False without flipping the banner.
    if completed and not interrupted:
        store.update_flags(task_done=True, busy=False, session_id=session_id or None)
    else:
        store.update_flags(busy=False, session_id=session_id or None)


def _on_pre_command(command: str = "", alias_used: str = "", **_kwargs) -> None:
    name = (command or alias_used or "").lower().lstrip("/")
    if name in _START_COMMANDS:
        store.update_flags(busy=True, task_done=False)
    elif name in {"new", "reset"}:
        store.update_flags(busy=False, task_done=False, wipe_on_escape=False)


def _on_subagent_stop(child_status: str = "", **_kwargs) -> None:
    # A child finishing is not the parent /goal finishing. Keep the flag file
    # in sync only when the child reports an obvious terminal success and the
    # parent looks idle — still best-effort.
    status = (child_status or "").lower()
    if status in {"completed", "success", "succeeded", "done"}:
        # Do not set task_done; parent may still be running.
        return


def _on_agent_loop_stopped(**kwargs) -> None:
    """Forward-compatible alias. Hermes does not fire this hook today."""
    completed = bool(kwargs.get("completed") or kwargs.get("success") or kwargs.get("done"))
    if completed:
        store.update_flags(task_done=True, busy=False)
    else:
        store.update_flags(busy=False)


def register(ctx) -> None:
    """Hermes ``register(ctx)`` entrypoint."""
    # Make this repo importable if Hermes loaded us via spec_from_file_location.
    root = Path(__file__).resolve().parent.parent
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)

    ctx.register_command(
        "console",
        handle_console,
        description="Open Console (Chrome dino). Esc returns to Hermes.",
    )
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("on_session_end", _on_session_end)
    ctx.register_hook("pre_command", _on_pre_command)
    ctx.register_hook("subagent_stop", _on_subagent_stop)
    ctx.register_hook("agent_loop_stopped", _on_agent_loop_stopped)
