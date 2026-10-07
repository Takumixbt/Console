import pytest

from console.games.dino import sound
from console.games.dino.demo import DemoDino
from console.gfx.sixel import SixelEncoder
from console.runner import compose, compute_layout


def test_sound_assets_are_real_wavs():
    import wave

    for name in sound.NAMES.values():
        with wave.open(str(sound.ASSETS / name)) as w:
            assert w.getnframes() > 1000


def test_sound_can_be_muted_and_never_raises(monkeypatch):
    monkeypatch.setenv("CONSOLE_SOUND", "0")
    s = sound.Sounds()
    s.play("press")
    s.play("not-a-sound")
    assert not s._on


def test_numpy_encoder_matches_the_pure_python_one():
    """Two independent implementations must emit the same bytes for real game frames."""
    pytest.importorskip("numpy")
    from console.gfx.sixel_np import NumpyEncoder

    g = DemoDino(seed=4)
    layout = compute_layout(120, 30, 10, 20, 600, 150)
    pure, fast = SixelEncoder(), NumpyEncoder()
    t = 0.0
    for i in range(900):
        t += 1000 / 60
        g.tick(t)
        if i % 37 == 0 and i > 100:
            f = g.frame(t)
            img = compose(f, layout)
            a = pure.encode(img, layout.width, layout.height, f.palette, layout.scale, f.page)
            b = fast.encode(img, layout.width, layout.height, f.palette, layout.scale, f.page)
            assert a == b
