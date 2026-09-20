"""Chrome T-Rex Runner constants (chromium ``offline.js`` / ``Trex.config``).

Units are pixels and frames at 60 FPS unless noted. Jump/gravity/speed
match Chrome so the feel survives the TUI scale.
"""

from __future__ import annotations

from dataclasses import dataclass

FPS = 60
MS_PER_FRAME = 1000.0 / FPS

# Runner.config / Runner.normalConfig
SPEED = 6.0
ACCELERATION = 0.001
MAX_SPEED = 13.0
CLEAR_TIME_MS = 3000
GAP_COEFFICIENT = 0.6
MAX_OBSTACLE_LENGTH = 3
MAX_OBSTACLE_DUPLICATION = 2
MAX_GAP_COEFFICIENT = 1.5
GAMEOVER_CLEAR_TIME_MS = 750
INVERT_SCORE = 700  # night mode on displayed-score milestones
BOTTOM_PAD = 10
CANVAS_HEIGHT = 150
DEFAULT_CANVAS_WIDTH = 600

# Trex.config (INIITAL_JUMP_VELOCITY is Chrome's historic misspelling)
GRAVITY = 0.6
INITIAL_JUMP_VELOCITY = -10.0
DROP_VELOCITY = -5.0
SPEED_DROP_COEFFICIENT = 3.0
MIN_JUMP_HEIGHT = 30
MAX_JUMP_HEIGHT_Y = 30  # absolute canvas Y at which endJump() is forced
TREX_WIDTH = 44
TREX_HEIGHT = 47
TREX_WIDTH_DUCK = 59
TREX_HEIGHT_DUCK = 25
TREX_START_X = 50

# DistanceMeter
SCORE_COEFFICIENT = 0.025  # displayed = round(distance_ran * 0.025)
SCORE_DIGITS = 5
ACHIEVEMENT_DISTANCE = 100

# Animation timings
RUN_MS_PER_FRAME = 1000.0 / 12
DUCK_MS_PER_FRAME = 1000.0 / 8
PTERO_MS_PER_FRAME = 1000.0 / 6
BLINK_MS = 7000

# Clouds (decorative)
CLOUD_SPEED = 0.2
CLOUD_MAX = 6
CLOUD_MIN_SKY_Y = 10
CLOUD_MAX_SKY_Y = 50


@dataclass(frozen=True)
class CollisionBox:
    x: float
    y: float
    w: float
    h: float

    def moved(self, dx: float, dy: float) -> CollisionBox:
        return CollisionBox(self.x + dx, self.y + dy, self.w, self.h)


# Trex.collisionBoxes — offsets relative to the +1 outer box (Chrome).
TREX_BOXES_RUNNING = (
    CollisionBox(22, 0, 17, 16),
    CollisionBox(1, 18, 30, 9),
    CollisionBox(10, 35, 14, 8),
    CollisionBox(1, 24, 29, 5),
    CollisionBox(5, 30, 21, 4),
    CollisionBox(9, 34, 15, 4),
)
TREX_BOXES_DUCKING = (CollisionBox(1, 18, 55, 25),)


@dataclass(frozen=True)
class ObstacleType:
    key: str
    width: int
    height: int
    y_pos: tuple[int, ...]
    multiple_speed: float
    min_gap: int
    min_speed: float
    boxes: tuple[CollisionBox, ...]
    num_frames: int = 1
    speed_offset: float = 0.0


CACTUS_SMALL = ObstacleType(
    key="CACTUS_SMALL",
    width=17,
    height=35,
    y_pos=(105,),
    multiple_speed=4,
    min_gap=120,
    min_speed=0.0,
    boxes=(
        CollisionBox(0, 7, 5, 27),
        CollisionBox(4, 0, 6, 34),
        CollisionBox(10, 4, 7, 14),
    ),
)
CACTUS_LARGE = ObstacleType(
    key="CACTUS_LARGE",
    width=25,
    height=50,
    y_pos=(90,),
    multiple_speed=7,
    min_gap=120,
    min_speed=0.0,
    boxes=(
        CollisionBox(0, 12, 7, 38),
        CollisionBox(8, 0, 7, 49),
        CollisionBox(13, 10, 10, 38),
    ),
)
PTERODACTYL = ObstacleType(
    key="PTERODACTYL",
    width=46,
    height=40,
    y_pos=(100, 75, 50),
    multiple_speed=999,
    min_gap=150,
    min_speed=8.5,
    boxes=(
        CollisionBox(15, 15, 16, 5),
        CollisionBox(18, 21, 24, 6),
        CollisionBox(2, 14, 4, 3),
        CollisionBox(6, 10, 4, 7),
        CollisionBox(10, 8, 6, 9),
    ),
    num_frames=2,
    speed_offset=0.8,
)

OBSTACLE_TYPES = (CACTUS_SMALL, CACTUS_LARGE, PTERODACTYL)
