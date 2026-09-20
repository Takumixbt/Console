from console.games.base import GameFlags, KeyEvent
from console.games.dino.constants import CLEAR_TIME_MS, MS_PER_FRAME, SPEED
from console.games.dino.game import DinoGame
from console.runner import run_headless


def test_idle_until_space():
    game = DinoGame(seed=1)
    game.update(100, GameFlags())
    assert game.waiting
    assert game.obstacles == []
    game.handle_key(KeyEvent("space", True))
    assert not game.waiting
    assert game.jumping


def test_jump_leaves_ground_and_returns():
    game = DinoGame(seed=1)
    game.handle_key(KeyEvent("space", True))
    ground = game.ground_y
    airborne = False
    for _ in range(90):
        game.update(MS_PER_FRAME, GameFlags())
        if game.y_pos < ground:
            airborne = True
    assert airborne
    assert game.y_pos == ground
    assert not game.jumping


def test_no_obstacles_before_clear_time():
    game = run_headless(frames=int(CLEAR_TIME_MS / MS_PER_FRAME) - 2, script=[(0, "space")], seed=2)
    assert game.obstacles == []
    assert not game.crashed


def test_cactus_eventually_hits_if_you_never_jump_again():
    # First space both starts the run and spends the intro jump. After landing,
    # stand still long enough for a cactus to arrive.
    game = run_headless(frames=800, script=[(0, "space")], seed=3)
    assert game.crashed


def test_score_tracks_distance():
    game = DinoGame(seed=1)
    game.handle_key(KeyEvent("space", True))
    for _ in range(60):
        game.update(MS_PER_FRAME, GameFlags())
    assert game.score() >= 0
    assert game.distance_ran > 0
    assert game.current_speed >= SPEED


def test_task_done_freezes_spawns():
    game = DinoGame(seed=7)
    game.handle_key(KeyEvent("space", True))
    flags = GameFlags()
    for _ in range(int(CLEAR_TIME_MS / MS_PER_FRAME) + 10):
        game.update(MS_PER_FRAME, flags)
    before = len(game.obstacles)
    flags.task_done = True
    for _ in range(240):
        game.update(MS_PER_FRAME, flags)
    assert game.saw_task_done_banner()
    # Existing obstacles may scroll off, but no replacements after freeze.
    assert len(game.obstacles) <= before


def test_render_has_ground_and_score():
    game = DinoGame(seed=1)
    game.handle_key(KeyEvent("space", True))
    for _ in range(30):
        game.update(MS_PER_FRAME, GameFlags())
    lines = game.render(80, 24)
    assert len(lines) == 24
    assert any("Console" in line for line in lines)
    joined = "\n".join(lines)
    assert "▀" in joined or "▄" in joined
    assert any(ch.isdigit() for ch in lines[0])


def test_snapshot_roundtrip():
    game = DinoGame(seed=4)
    game.handle_key(KeyEvent("space", True))
    for _ in range(200):
        game.update(MS_PER_FRAME, GameFlags())
    snap = game.snapshot()
    other = DinoGame(seed=99)
    other.load_snapshot(snap)
    assert other.distance_ran == game.distance_ran
    assert other.y_pos == game.y_pos
    assert len(other.obstacles) == len(game.obstacles)
