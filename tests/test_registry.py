from console.catalog import DEFAULT_GAME, GAMES
from console.registry import get_game


def test_dino_is_default():
    assert DEFAULT_GAME == "dino"
    assert "dino" in GAMES
    game = get_game()
    assert game.name == "dino"


def test_unknown_game():
    try:
        get_game("chess")
    except KeyError as exc:
        assert "chess" in str(exc)
    else:
        raise AssertionError("expected KeyError")
