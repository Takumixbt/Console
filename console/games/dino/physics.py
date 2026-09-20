"""AABB collision and Chrome-style box adjustment."""

from __future__ import annotations

from .constants import (
    TREX_BOXES_DUCKING,
    TREX_BOXES_RUNNING,
    TREX_HEIGHT,
    TREX_WIDTH,
    CollisionBox,
)


def boxes_overlap(a: CollisionBox, b: CollisionBox) -> bool:
    return a.x < b.x + b.w and a.x + a.w > b.x and a.y < b.y + b.h and a.y + a.h > b.y


def adjust(box: CollisionBox, origin: CollisionBox) -> CollisionBox:
    """Chrome ``createAdjustedCollisionBox``."""
    return CollisionBox(box.x + origin.x, box.y + origin.y, box.w, box.h)


def trex_outer(x: float, y: float) -> CollisionBox:
    return CollisionBox(x + 1, y + 1, TREX_WIDTH - 2, TREX_HEIGHT - 2)


def obstacle_outer(x: float, y: float, width: float, height: float) -> CollisionBox:
    return CollisionBox(x + 1, y + 1, width - 2, height - 2)


def crashed(
    trex_x: float,
    trex_y: float,
    ducking: bool,
    obst_x: float,
    obst_y: float,
    obst_w: float,
    obst_h: float,
    obst_boxes: tuple[CollisionBox, ...],
) -> bool:
    """Two-phase Chrome collision: outer AABB, then inner sprite boxes."""
    t_outer = trex_outer(trex_x, trex_y)
    o_outer = obstacle_outer(obst_x, obst_y, obst_w, obst_h)
    if not boxes_overlap(t_outer, o_outer):
        return False
    inner = TREX_BOXES_DUCKING if ducking else TREX_BOXES_RUNNING
    for tb in inner:
        adj_t = adjust(tb, t_outer)
        for ob in obst_boxes:
            if boxes_overlap(adj_t, adjust(ob, o_outer)):
                return True
    return False
