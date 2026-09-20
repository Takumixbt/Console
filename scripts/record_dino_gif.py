#!/usr/bin/env python3
"""Record a short Console dino clip into docs/console-dino.gif.

Plays the real game engine (same renderer as the TUI) with a small
auto-jumper and draws each sampled frame with DejaVu Sans Mono.
Re-run from the repo root:

    python3 -m pip install pillow
    python3 scripts/record_dino_gif.py

Pillow writes the GIF. ffmpeg is optional for a tighter palette.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from console.games.base import GameFlags, KeyEvent
from console.games.dino.constants import MS_PER_FRAME, TREX_WIDTH
from console.games.dino.game import DinoGame

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "console-dino.gif"
FONT_CANDIDATES = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Regular.ttf"),
    Path("/usr/share/fonts/TTF/DejaVuSansMono.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"),
    Path("/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf"),
)

COLS = 80
ROWS = 22
FONT_SIZE = 15
PAD_X = 18
PAD_Y = 16
TITLE_H = 28
FPS = 16
SAMPLE_EVERY = 4  # 60fps sim -> 15-16 displayed fps
PLAY_FRAMES = 640
SEED = 23
TRIGGER = 70.0

BG = (13, 13, 15)
PANEL = (20, 20, 23)
FG = (210, 210, 210)
DIM = (140, 140, 146)
TITLE = (235, 235, 235)
DOT_RED = (255, 95, 87)
DOT_YELLOW = (254, 188, 46)
DOT_GREEN = (40, 200, 64)


def _auto_play(game: DinoGame) -> None:
    if game.crashed or game.waiting or game.jumping:
        return
    if not game.obstacles:
        return
    obst = game.obstacles[0]
    dist = obst.x - (game.x_pos + TREX_WIDTH)
    high_ptero = obst.kind.key == "PTERODACTYL" and obst.y <= 55
    if high_ptero:
        game.handle_key(KeyEvent("down", True))
        return
    game.handle_key(KeyEvent("down", False))
    if 0 < dist < TRIGGER + game.current_speed * 8:
        game.handle_key(KeyEvent("space", True))
        game.handle_key(KeyEvent("space", False))


def _cell_size(font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = font.getbbox("M")
    return max(6, bbox[2] - bbox[0]), max(12, bbox[3] - bbox[1] + 4)


def _line_color(line: str) -> tuple[int, int, int]:
    if "TASK DONE" in line:
        return (63, 185, 80)
    if "G A M E" in line:
        return (248, 81, 73)
    if line.startswith("Console"):
        return TITLE
    if "jump" in line.lower() or "Esc" in line:
        return DIM
    return FG


def collect_lines() -> list[list[str]]:
    game = DinoGame(seed=SEED)
    game.handle_key(KeyEvent("space", True))
    frames: list[list[str]] = []
    for i in range(PLAY_FRAMES):
        _auto_play(game)
        game.update(MS_PER_FRAME, GameFlags())
        if i % SAMPLE_EVERY == 0:
            frames.append(game.render(COLS, ROWS))
        if game.crashed:
            frames.append(game.render(COLS, ROWS))
            break
    return frames


def draw_frame(lines: list[str], font: ImageFont.ImageFont, cw: int, ch: int) -> Image.Image:
    width = PAD_X * 2 + cw * COLS
    height = PAD_Y * 2 + TITLE_H + ch * ROWS
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        (8, 8, width - 9, height - 9),
        radius=10,
        fill=PANEL,
        outline=(50, 50, 56),
    )
    for color, x in ((DOT_RED, 22), (DOT_YELLOW, 40), (DOT_GREEN, 58)):
        draw.ellipse((x, 16, x + 10, 26), fill=color)
    draw.text((78, 14), "Console", font=font, fill=TITLE)
    y = PAD_Y + TITLE_H
    for line in lines:
        draw.text((PAD_X, y), line, font=font, fill=_line_color(line))
        y += ch
    return img


def encode_gif_pillow(images: list[Image.Image]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    quantized = [
        im.convert("P", palette=Image.Palette.ADAPTIVE, colors=48) for im in images
    ]
    quantized[0].save(
        OUT,
        save_all=True,
        append_images=quantized[1:],
        duration=int(round(1000 / FPS)),
        loop=0,
        optimize=True,
        disposal=2,
    )


def encode_gif_ffmpeg(frame_dir: Path) -> None:
    palette = frame_dir / "palette.png"
    pattern = str(frame_dir / "frame_%04d.png")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            pattern,
            "-vf",
            "palettegen=max_colors=56:stats_mode=diff",
            str(palette),
        ],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            pattern,
            "-i",
            str(palette),
            "-lavfi",
            "paletteuse=dither=bayer:bayer_scale=3",
            "-loop",
            "0",
            str(OUT),
        ],
        check=True,
    )


def _load_font() -> ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if path.is_file():
            return ImageFont.truetype(str(path), FONT_SIZE)
    return ImageFont.load_default()


def main() -> int:
    font = _load_font()
    cw, ch = _cell_size(font)
    frames = collect_lines()
    images = [draw_frame(lines, font, cw, ch) for lines in frames]
    used = "pillow"
    if shutil.which("ffmpeg"):
        with tempfile.TemporaryDirectory(prefix="console-gif-") as tmp:
            tmp_path = Path(tmp)
            for i, im in enumerate(images):
                im.save(tmp_path / f"frame_{i:04d}.png")
            try:
                encode_gif_ffmpeg(tmp_path)
                used = "ffmpeg"
            except (OSError, subprocess.CalledProcessError) as exc:
                print(f"ffmpeg failed ({exc}); using Pillow", file=sys.stderr)
                encode_gif_pillow(images)
    else:
        encode_gif_pillow(images)
    if not OUT.is_file() or OUT.stat().st_size < 32:
        raise SystemExit(f"did not write a GIF at {OUT}")
    header = OUT.read_bytes()[:6]
    if header not in (b"GIF87a", b"GIF89a"):
        raise SystemExit(f"output is not a GIF: {header!r}")
    size = OUT.stat().st_size
    print(f"wrote {OUT} ({len(frames)} frames, {size / 1024:.1f} KB, {used})")
    if size > 8 * 1024 * 1024:
        print("warning: GIF is larger than 8 MB", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
