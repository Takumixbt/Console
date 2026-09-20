#!/usr/bin/env python3
"""Write a GIF that uses only bytes 0-127 so text-only Git APIs can store it.

Used as a fallback if a binary push is unavailable. The Action workflow
overwrites docs/console-dino.gif with the full-color recording.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "console-dino.gif"
OUT = Path("/tmp/console-dino-7bit.gif")

# Width/height bytes must each be < 128. 639 = 0x027F, 255 cannot use 0xFF.
WIDTH = 639
HEIGHT = 375


def _assert_7bit(data: bytes, label: str) -> None:
    high = [b for b in data if b > 127]
    if high:
        raise SystemExit(f"{label}: found bytes > 127 (e.g. {high[:8]})")


def _u16(n: int) -> bytes:
    lo, hi = n & 0xFF, (n >> 8) & 0xFF
    if lo > 127 or hi > 127:
        raise ValueError(f"cannot encode {n} as 7-bit LE u16")
    return bytes((lo, hi))


def _pack_codes(codes: list[int], code_size: int) -> bytearray:
    bits: list[int] = []
    for code in codes:
        for i in range(code_size):
            bits.append((code >> i) & 1)
    out = bytearray()
    for i in range(0, len(bits), 8):
        chunk = bits[i : i + 8]
        while len(chunk) < 8:
            chunk.append(0)
        value = 0
        for bit_i, bit in enumerate(chunk):
            value |= bit << bit_i
        if value > 127:
            # Should not happen with our 3-bit codes and alignment padding.
            raise RuntimeError(f"packed byte {value}")
        out.append(value)
    return out


def _image_data(indexes: list[int]) -> bytes:
    """Uncompressed LZW, min code size 2 (4 colors). Codes are 3 bits."""
    min_code_size = 2
    clear, eoi = 4, 5
    codes = [clear]
    for i, pix in enumerate(indexes):
        codes.append(pix & 3)
        if (i + 1) % 12 == 0:
            codes.append(clear)
    codes.append(eoi)
    packed = _pack_codes(codes, 3)
    blocks = bytearray()
    blocks.append(min_code_size)
    for i in range(0, len(packed), 127):
        chunk = packed[i : i + 127]
        blocks.append(len(chunk))
        blocks.extend(chunk)
    blocks.append(0)
    _assert_7bit(bytes(blocks), "image data")
    return bytes(blocks)


def _frame_indexes(img: Image.Image) -> list[int]:
    gray = img.convert("L").resize((WIDTH, HEIGHT), Image.Resampling.BILINEAR)
    pixels = list(gray.getdata())
    out = []
    for p in pixels:
        if p < 40:
            out.append(0)
        elif p < 90:
            out.append(1)
        elif p < 160:
            out.append(2)
        else:
            out.append(3)
    return out


def encode(frames: list[Image.Image]) -> bytes:
    # Global color table: 4 colors, all channels <= 127.
    gct = bytes(
        [
            13, 13, 15,
            70, 70, 74,
            100, 100, 104,
            126, 126, 126,
        ]
    )
    # packed: GCT=1, color res=1, sort=0, GCT size=1 -> 2^(1+1)=4 colors
    packed_screen = 0b10000001
    header = b"GIF89a" + _u16(WIDTH) + _u16(HEIGHT) + bytes((packed_screen, 0, 0)) + gct
    _assert_7bit(header, "header")

    body = bytearray(header)
    for img in frames:
        indexes = _frame_indexes(img)
        # Image descriptor. Packed: no LCT.
        desc = b"," + _u16(0) + _u16(0) + _u16(WIDTH) + _u16(HEIGHT) + bytes((0,))
        _assert_7bit(desc, "descriptor")
        body.extend(desc)
        body.extend(_image_data(indexes))
    body.append(0x3B)
    _assert_7bit(bytes(body), "gif")
    return bytes(body)


def main() -> None:
    src = Image.open(SRC)
    picked: list[Image.Image] = []
    # ~16 frames across the clip, each duplicated so it holds on screen.
    total = getattr(src, "n_frames", 1)
    targets = [round(i * (total - 1) / 15) for i in range(16)]
    for idx in targets:
        src.seek(idx)
        frame = src.convert("RGB").copy()
        picked.extend([frame, frame])
    data = encode(picked)
    OUT.write_bytes(data)
    print(f"wrote 7-bit GIF {OUT} ({len(data) / 1024:.1f} KB, {len(picked)} frames)")


if __name__ == "__main__":
    main()
