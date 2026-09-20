#!/usr/bin/env python3
"""Write docs/console-dino.svg from the real dino renderer.

Text-only, so it can be pushed through APIs that reject binary GIFs.
GitHub may freeze SMIL; the first frame still shows a jump over a cactus.
"""

from __future__ import annotations

import html
from pathlib import Path

from console.games.base import GameFlags, KeyEvent
from console.games.dino.constants import MS_PER_FRAME, TREX_WIDTH
from console.games.dino.game import DinoGame

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "console-dino.svg"
COLS, ROWS = 80, 22
SEED, TRIGGER = 23, 70.0
HOLD_MS = 120


def _auto_play(game: DinoGame) -> None:
    if game.crashed or game.waiting or game.jumping or not game.obstacles:
        return
    obst = game.obstacles[0]
    dist = obst.x - (game.x_pos + TREX_WIDTH)
    if obst.kind.key == "PTERODACTYL" and obst.y <= 55:
        game.handle_key(KeyEvent("down", True))
        return
    game.handle_key(KeyEvent("down", False))
    if 0 < dist < TRIGGER + game.current_speed * 8:
        game.handle_key(KeyEvent("space", True))
        game.handle_key(KeyEvent("space", False))


def collect() -> list[str]:
    game = DinoGame(seed=SEED)
    game.handle_key(KeyEvent("space", True))
    clips: list[str] = []
    for i in range(640):
        _auto_play(game)
        game.update(MS_PER_FRAME, GameFlags())
        if i % 24 == 0:
            clips.append("\n".join(game.render(COLS, ROWS)))
        if game.crashed:
            break
    return clips


def main() -> None:
    clips = collect()
    cycle = len(clips) * HOLD_MS
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 430" '
        'role="img" aria-label="Console dino: jump over cacti, score ticking">',
        '<rect width="100%" height="100%" rx="12" fill="#0d0d0f"/>',
        '<circle cx="22" cy="18" r="5" fill="#ff5f57"/>',
        '<circle cx="40" cy="18" r="5" fill="#febc2e"/>',
        '<circle cx="58" cy="18" r="5" fill="#28c840"/>',
        '<text x="78" y="23" fill="#ebebeb" font-size="13" '
        'font-family="ui-monospace, SFMono-Regular, DejaVu Sans Mono, monospace">Console</text>',
    ]
    for i, text in enumerate(clips):
        begin = i * HOLD_MS
        # Frame 0 stays visible if SMIL is stripped.
        display = "inline" if i == 0 else "none"
        anim = ""
        if i == 0:
            anim = (
                f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;{HOLD_MS/cycle:.4f};{HOLD_MS/cycle:.4f};1" '
                f'dur="{cycle}ms" repeatCount="indefinite"/>'
            )
        else:
            start = begin / cycle
            end = (begin + HOLD_MS) / cycle
            anim = (
                f'<animate attributeName="opacity" values="0;0;1;1;0;0" '
                f'keyTimes="0;{start:.4f};{start:.4f};{end:.4f};{end:.4f};1" '
                f'dur="{cycle}ms" repeatCount="indefinite"/>'
            )
        parts.append(
            f'<text xml:space="preserve" x="18" y="48" fill="#d2d2d2" font-size="11" '
            f'font-family="ui-monospace, SFMono-Regular, DejaVu Sans Mono, monospace" '
            f'style="white-space:pre" opacity="{"1" if i == 0 else "0"}">'
            f"{html.escape(text)}{anim}</text>"
        )
        del display
    parts.append("</svg>")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.1f} KB, {len(clips)} frames)")


if __name__ == "__main__":
    main()
