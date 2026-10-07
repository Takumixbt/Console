import pytest

from console import registry
from console.catalog import DEFAULT_GAME, GAMES


def test_dino_is_registered_and_default():
    assert DEFAULT_GAME == "dino"
    assert "dino" in GAMES


def test_a_game_is_created_once_per_process(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    registry.forget()
    a = registry.get_game("dino")
    assert registry.get_game("DINO") is a
    registry.forget("dino")
    assert registry.get_game() is not a


def test_unknown_game_lists_the_known_ones():
    with pytest.raises(KeyError, match="dino"):
        registry.get_game("pong")
