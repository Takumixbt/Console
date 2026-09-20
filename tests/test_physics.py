from console.games.dino.constants import (
    CACTUS_SMALL,
    TREX_HEIGHT,
    TREX_START_X,
    TREX_WIDTH,
)
from console.games.dino.physics import boxes_overlap, crashed
from console.games.dino.constants import CollisionBox


def test_aabb_overlap_and_gap():
    a = CollisionBox(0, 0, 10, 10)
    b = CollisionBox(5, 5, 10, 10)
    c = CollisionBox(20, 0, 10, 10)
    assert boxes_overlap(a, b)
    assert not boxes_overlap(a, c)


def test_dino_hits_overlapping_cactus():
    # Standing dino at Chrome start; cactus planted on its body.
    assert crashed(
        TREX_START_X,
        93,
        False,
        TREX_START_X + 8,
        105,
        CACTUS_SMALL.width,
        CACTUS_SMALL.height,
        CACTUS_SMALL.boxes,
    )


def test_dino_misses_distant_cactus():
    assert not crashed(
        TREX_START_X,
        93,
        False,
        400,
        105,
        CACTUS_SMALL.width,
        CACTUS_SMALL.height,
        CACTUS_SMALL.boxes,
    )


def test_outer_box_sizes():
    assert TREX_WIDTH == 44
    assert TREX_HEIGHT == 47
