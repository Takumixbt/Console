"""A second, independent sixel encoder written with numpy.

It is not used at run time: the cached pure-Python encoder in ``sixel.py`` is
faster for game frames, where most bands repeat from one frame to the next. It
stays as a cross-check, because two implementations that share no code must
produce the same bytes (see ``tests/test_sound_and_encoders.py``). The whole
frame is packed at once: one boolean mask per colour, six mask rows folded into
one sixel byte per band column with a weighted sum, and run boundaries found
with a single vectorised comparison.
"""

from __future__ import annotations

import numpy as np

from .sixel import _percent


class NumpyEncoder:
    def __init__(self) -> None:
        self._plans: dict[tuple[int, int], tuple] = {}

    def _plan(self, height: int, scale: int):
        plan = self._plans.get((height, scale))
        if plan is None:
            out_h = height * scale
            nb = (out_h + 5) // 6
            ys = np.empty((nb, 6), dtype=np.intp)
            valid = np.empty((nb, 6), dtype=bool)
            for band in range(nb):
                for k in range(6):
                    r = band * 6 + k
                    ys[band, k] = min(height - 1, r // scale)
                    valid[band, k] = r < out_h
            weights = (valid * (1 << np.arange(6))).astype(np.uint8)  # (nb, 6): 0 for rows below the picture
            valid_bits = weights.sum(axis=1).astype(np.uint8)
            plan = self._plans[(height, scale)] = (ys, weights, valid_bits)
        return plan

    def encode(self, pixels: bytes, width: int, height: int, palette, scale: int = 1, page: int | None = None) -> bytes:
        ys, weights, valid_bits = self._plan(height, scale)
        nb = ys.shape[0]
        image = np.frombuffer(pixels, dtype=np.uint8).reshape(height, width)
        colors = [int(c) for c in np.unique(image) if c != page]

        pieces: list[list[bytes]] = [[] for _ in range(nb)]
        used: list[int] = []
        if page is not None:
            used.append(page)
            bits = (valid_bits + 63).tolist()
            run = width * scale
            for b in range(nb):
                pieces[b].append(b"#%d!%d%c" % (page, run, bits[b]))
        w3 = weights[:, :, None]
        for c in colors:
            mask = (image == c).astype(np.uint8)
            value = (mask[ys] * w3).sum(axis=1, dtype=np.uint8)  # (nb, width), 0..63
            present = np.flatnonzero(value.any(axis=1))
            if not len(present):
                continue
            used.append(c)
            chars = value + np.uint8(63)
            head = b"#%d" % c
            diff = chars[:, 1:] != chars[:, :-1]
            for b in present.tolist():
                row = chars[b]
                ends = np.flatnonzero(diff[b])
                starts = np.concatenate(([0], ends + 1))
                stops = np.concatenate((ends + 1, [width]))
                out = [head]
                for length, ch in zip(((stops - starts) * scale).tolist(), row[starts].tolist()):
                    out.append(b"!%d%c" % (length, ch) if length > 3 else bytes((ch,)) * length)
                pieces[b].append(b"".join(out))

        head = [b"\x1bP0;1;0q\"1;1;%d;%d" % (width * scale, height * scale)]
        for index in sorted(used):
            r, g, bl = palette[index]
            head.append(b"#%d;2;%d;%d;%d" % (index, _percent(r), _percent(g), _percent(bl)))
        body = b"".join(b"$".join(p) + b"-" for p in pieces)
        return b"".join(head) + body + b"\x1b\\"
