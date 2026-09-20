import importlib.util
import sys
import types
from pathlib import Path

from console.hermes_plugin import handle_console, register
from console.runner import CLI_ONLY


class FakeCtx:
    def __init__(self):
        self.commands = {}
        self.hooks = {}

    def register_command(self, name, handler, description=""):
        self.commands[name] = (handler, description)

    def register_hook(self, name, callback):
        self.hooks.setdefault(name, []).append(callback)


def test_register_wires_slash_command_and_hooks():
    ctx = FakeCtx()
    register(ctx)
    assert "console" in ctx.commands
    handler, description = ctx.commands["console"]
    assert "dino" in description.lower() or "console" in description.lower()
    assert handler is handle_console
    for name in ("on_session_start", "on_session_end", "pre_command", "subagent_stop"):
        assert name in ctx.hooks
    assert "agent_loop_stopped" in ctx.hooks


def test_handler_rejects_non_tty(monkeypatch):
    monkeypatch.setattr("console.hermes_plugin.is_tty", lambda: False)
    assert handle_console("") == CLI_ONLY


def test_handler_rejects_gateway(monkeypatch):
    monkeypatch.setenv("HERMES_GATEWAY", "1")
    monkeypatch.setattr("console.hermes_plugin.is_tty", lambda: True)
    assert "CLI" in handle_console("")


def test_hermes_style_root_import():
    root = Path(__file__).resolve().parents[1]
    ns = "hermes_plugins"
    if ns not in sys.modules:
        pkg = types.ModuleType(ns)
        pkg.__path__ = []
        sys.modules[ns] = pkg
    name = f"{ns}.console_test"
    spec = importlib.util.spec_from_file_location(
        name,
        root / "__init__.py",
        submodule_search_locations=[str(root)],
    )
    module = importlib.util.module_from_spec(spec)
    module.__package__ = name
    module.__path__ = [str(root)]
    sys.modules[name] = module
    spec.loader.exec_module(module)
    assert callable(module.register)
    ctx = FakeCtx()
    module.register(ctx)
    assert "console" in ctx.commands
