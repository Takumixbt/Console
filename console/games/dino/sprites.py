"""ASCII / block-character frames approximating Chrome's T-Rex sprites."""

from __future__ import annotations

# Each frame is a list of equal-width rows. Spaces are transparent.

DINO_RUN_1 = (
    "          ▄█▄",
    "         █████",
    "    ▄    ██▀▀█",
    "    ████████▀ ",
    "     ██████   ",
    "      █  █    ",
)
DINO_RUN_2 = (
    "          ▄█▄",
    "         █████",
    "    ▄    ██▀▀█",
    "    ████████▀ ",
    "     ██████   ",
    "     █    █   ",
)
DINO_JUMP = (
    "          ▄█▄",
    "         █████",
    "    ▄    ██▀▀█",
    "    ████████▀ ",
    "     ██████   ",
    "      ▀  ▀    ",
)
DINO_WAIT = (
    "          ▄█▄",
    "         █████",
    "    ▄    ██▀▀█",
    "    ████████▀ ",
    "     ██████   ",
    "      █  █    ",
)
DINO_BLINK = (
    "          ▄█▄",
    "         █████",
    "    ▄    ██▄▄█",
    "    ████████▀ ",
    "     ██████   ",
    "      █  █    ",
)
DINO_DEAD = (
    "          ▄█▄",
    "         ██x██",
    "    ▄    ██▀▀█",
    "    ████████▀ ",
    "     ██████   ",
    "      █  █    ",
)
DINO_DUCK_1 = (
    "█   ▄▄████████▄",
    "█████████▀▀▀███",
    " ███████████▀  ",
    "  █       █    ",
)
DINO_DUCK_2 = (
    "█   ▄▄████████▄",
    "█████████▀▀▀███",
    " ███████████▀  ",
    "    █   █      ",
)

CACTUS_SMALL = (
    " ▐▌ ",
    "▌▐█▌",
    " ▐█ ",
    " ▐█ ",
    " ▐█ ",
)
CACTUS_LARGE = (
    "  ▂  ",
    " ▐█▌ ",
    "▌▐█▌▐",
    "  █  ",
    "  █  ",
    "  █  ",
    "  █  ",
)
PTERO_1 = (
    "  ▄▀▄▄  ",
    "▀██████▀",
    "  ▀▀▀   ",
)
PTERO_2 = (
    "   ▄▄   ",
    "▀██████▀",
    " ▀▄  ▄▀ ",
)
CLOUD = (
    "  ▄▄▄  ",
    "▄█████▄",
)

GROUND_TILES = "▀▀▀▀▄▀▀▀▀▀▀▃▀▀▀▀▀▀▀▄▀▀▀▀"


def _pad(rows: tuple[str, ...]) -> tuple[str, ...]:
    width = max(len(r) for r in rows)
    return tuple(r.ljust(width) for r in rows)


def blit(buf: list[list[str]], rows: tuple[str, ...], col: int, row: int) -> None:
    """Stamp non-space characters onto a character buffer."""
    if not buf:
        return
    height = len(buf)
    width = len(buf[0])
    for dy, line in enumerate(rows):
        y = row + dy
        if y < 0 or y >= height:
            continue
        for dx, ch in enumerate(line):
            if ch == " ":
                continue
            x = col + dx
            if 0 <= x < width:
                buf[y][x] = ch


DINO_RUN_1 = _pad(DINO_RUN_1)
DINO_RUN_2 = _pad(DINO_RUN_2)
DINO_JUMP = _pad(DINO_JUMP)
DINO_WAIT = _pad(DINO_WAIT)
DINO_BLINK = _pad(DINO_BLINK)
DINO_DEAD = _pad(DINO_DEAD)
DINO_DUCK_1 = _pad(DINO_DUCK_1)
DINO_DUCK_2 = _pad(DINO_DUCK_2)
CACTUS_SMALL = _pad(CACTUS_SMALL)
CACTUS_LARGE = _pad(CACTUS_LARGE)
PTERO_1 = _pad(PTERO_1)
PTERO_2 = _pad(PTERO_2)
CLOUD = _pad(CLOUD)
