"""Playable Chrome-dino replica. Physics stay in Chrome pixel space."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from ...catalog import register
from ..base import GameFlags, KeyEvent
from . import sprites
from .constants import (
    ACCELERATION,
    ACHIEVEMENT_DISTANCE,
    BOTTOM_PAD,
    CANVAS_HEIGHT,
    CACTUS_LARGE,
    CACTUS_SMALL,
    CLEAR_TIME_MS,
    CLOUD_MAX,
    CLOUD_MAX_SKY_Y,
    CLOUD_MIN_SKY_Y,
    CLOUD_SPEED,
    DEFAULT_CANVAS_WIDTH,
    DROP_VELOCITY,
    GAP_COEFFICIENT,
    GRAVITY,
    INITIAL_JUMP_VELOCITY,
    INVERT_SCORE,
    MAX_GAP_COEFFICIENT,
    MAX_JUMP_HEIGHT_Y,
    MAX_OBSTACLE_DUPLICATION,
    MAX_OBSTACLE_LENGTH,
    MAX_SPEED,
    MIN_JUMP_HEIGHT,
    MS_PER_FRAME,
    OBSTACLE_TYPES,
    PTERO_MS_PER_FRAME,
    PTERODACTYL,
    RUN_MS_PER_FRAME,
    DUCK_MS_PER_FRAME,
    SCORE_COEFFICIENT,
    SCORE_DIGITS,
    SPEED,
    SPEED_DROP_COEFFICIENT,
    TREX_HEIGHT,
    TREX_START_X,
    CollisionBox,
    ObstacleType,
)
from .physics import crashed


def _rand_int(rng: random.Random, lo: int, hi: int) -> int:
    """Chrome ``getRandomNum`` — inclusive on both ends."""
    return rng.randint(lo, hi)


@dataclass
class Obstacle:
    kind: ObstacleType
    x: float
    y: float
    size: int
    gap: float
    speed_offset: float
    boxes: tuple[CollisionBox, ...]
    frame: int = 0
    timer: float = 0.0
    following_created: bool = False

    @property
    def width(self) -> int:
        return self.kind.width * self.size

    @property
    def height(self) -> int:
        return self.kind.height

    def visible(self) -> bool:
        return self.x + self.width > 0


@dataclass
class Cloud:
    x: float
    y: float


@dataclass
class DinoGame:
    name: str = "dino"
    seed: int | None = None

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)
        self.canvas_width = float(DEFAULT_CANVAS_WIDTH)
        self.high_score = 0
        self._saw_banner = False
        self._flash_score = False
        self._flash_timer = 0.0
        self.reset()

    # -- lifecycle --------------------------------------------------------

    def reset(self) -> None:
        self.waiting = True
        self.crashed = False
        self.playing_started = False
        self.running_time = 0.0
        self.distance_ran = 0.0
        self.current_speed = SPEED
        self.horizon = 0.0
        self.obstacles: list[Obstacle] = []
        self.obstacle_history: list[str] = []
        self.clouds: list[Cloud] = []
        self.x_pos = float(TREX_START_X)
        self.ground_y = float(CANVAS_HEIGHT - TREX_HEIGHT - BOTTOM_PAD)
        self.y_pos = self.ground_y
        self.jump_velocity = 0.0
        self.jumping = False
        self.ducking = False
        self.reached_min_height = False
        self.speed_drop = False
        self.down_held = False
        self.jump_held = False
        self.anim_timer = 0.0
        self.anim_frame = 0
        self.blink_on = False
        self.blink_timer = 0.0
        self._saw_banner = False
        self._spawn_frozen = False
        self._inverted = False

    def snapshot(self) -> dict[str, Any]:
        return {
            "waiting": self.waiting,
            "crashed": self.crashed,
            "playing_started": self.playing_started,
            "running_time": self.running_time,
            "distance_ran": self.distance_ran,
            "current_speed": self.current_speed,
            "horizon": self.horizon,
            "x_pos": self.x_pos,
            "y_pos": self.y_pos,
            "jump_velocity": self.jump_velocity,
            "jumping": self.jumping,
            "ducking": self.ducking,
            "reached_min_height": self.reached_min_height,
            "speed_drop": self.speed_drop,
            "down_held": self.down_held,
            "jump_held": self.jump_held,
            "anim_timer": self.anim_timer,
            "anim_frame": self.anim_frame,
            "high_score": self.high_score,
            "canvas_width": self.canvas_width,
            "obstacles": [
                {
                    "key": o.kind.key,
                    "x": o.x,
                    "y": o.y,
                    "size": o.size,
                    "gap": o.gap,
                    "speed_offset": o.speed_offset,
                    "frame": o.frame,
                    "timer": o.timer,
                    "following_created": o.following_created,
                    "boxes": [(b.x, b.y, b.w, b.h) for b in o.boxes],
                }
                for o in self.obstacles
            ],
            "obstacle_history": list(self.obstacle_history),
            "clouds": [{"x": c.x, "y": c.y} for c in self.clouds],
        }

    def load_snapshot(self, data: dict[str, Any]) -> None:
        self.waiting = bool(data.get("waiting", False))
        self.crashed = bool(data.get("crashed", False))
        self.playing_started = bool(data.get("playing_started", not self.waiting))
        self.running_time = float(data.get("running_time", 0.0))
        self.distance_ran = float(data.get("distance_ran", 0.0))
        self.current_speed = float(data.get("current_speed", SPEED))
        self.horizon = float(data.get("horizon", 0.0))
        self.x_pos = float(data.get("x_pos", TREX_START_X))
        self.y_pos = float(data.get("y_pos", self.ground_y))
        self.jump_velocity = float(data.get("jump_velocity", 0.0))
        self.jumping = bool(data.get("jumping", False))
        self.ducking = bool(data.get("ducking", False))
        self.reached_min_height = bool(data.get("reached_min_height", False))
        self.speed_drop = bool(data.get("speed_drop", False))
        self.down_held = bool(data.get("down_held", False))
        self.jump_held = bool(data.get("jump_held", False))
        self.anim_timer = float(data.get("anim_timer", 0.0))
        self.anim_frame = int(data.get("anim_frame", 0))
        self.high_score = max(self.high_score, int(data.get("high_score", 0)))
        self.canvas_width = float(data.get("canvas_width", self.canvas_width))
        kinds = {t.key: t for t in OBSTACLE_TYPES}
        self.obstacles = []
        for raw in data.get("obstacles") or []:
            kind = kinds.get(raw.get("key", ""), CACTUS_SMALL)
            boxes = tuple(
                CollisionBox(*b) for b in raw.get("boxes") or [(box.x, box.y, box.w, box.h) for box in kind.boxes]
            )
            self.obstacles.append(
                Obstacle(
                    kind=kind,
                    x=float(raw.get("x", 0)),
                    y=float(raw.get("y", kind.y_pos[0])),
                    size=int(raw.get("size", 1)),
                    gap=float(raw.get("gap", 120)),
                    speed_offset=float(raw.get("speed_offset", 0)),
                    boxes=boxes,
                    frame=int(raw.get("frame", 0)),
                    timer=float(raw.get("timer", 0)),
                    following_created=bool(raw.get("following_created", False)),
                )
            )
        self.obstacle_history = list(data.get("obstacle_history") or [])
        self.clouds = [Cloud(float(c["x"]), float(c["y"])) for c in data.get("clouds") or []]

    def saw_task_done_banner(self) -> bool:
        return self._saw_banner

    # -- input ------------------------------------------------------------

    def handle_key(self, event: KeyEvent) -> None:
        name = event.name
        if name in {"space", "up"}:
            if event.pressed:
                self.jump_held = True
                self._on_jump()
            else:
                self.jump_held = False
                self._end_jump()
        elif name == "down":
            if event.pressed:
                self.down_held = True
                self._on_down()
            else:
                self.down_held = False
                self._on_down_release()

    def _on_jump(self) -> None:
        if self.crashed:
            self.reset()
            self._start_run(initial_jump=True)
            return
        if self.waiting:
            self._start_run(initial_jump=True)
            return
        if not self.jumping and not self.ducking:
            self._start_jump()

    def _start_run(self, initial_jump: bool) -> None:
        self.waiting = False
        self.crashed = False
        self.playing_started = True
        self.running_time = 0.0
        if initial_jump:
            self._start_jump()

    def _start_jump(self) -> None:
        if self.jumping:
            return
        self.jumping = True
        self.ducking = False
        self.reached_min_height = False
        self.speed_drop = False
        self.jump_velocity = INITIAL_JUMP_VELOCITY - (self.current_speed / 10.0)
        self.anim_frame = 0
        self.anim_timer = 0.0

    def _end_jump(self) -> None:
        if self.reached_min_height and self.jump_velocity < DROP_VELOCITY:
            self.jump_velocity = DROP_VELOCITY

    def _on_down(self) -> None:
        if self.waiting or self.crashed:
            return
        if self.jumping:
            self.speed_drop = True
            self.jump_velocity = 1.0
        elif not self.jumping:
            self.ducking = True

    def _on_down_release(self) -> None:
        if not self.jumping:
            self.ducking = False

    # -- update -----------------------------------------------------------

    def update(self, dt_ms: float, flags: GameFlags) -> None:
        if flags.task_done:
            self._saw_banner = True
            self._spawn_frozen = True
        if self.waiting:
            self._update_wait(dt_ms)
            self._maybe_cloud(dt_ms, moving=False)
            return
        if self.crashed:
            return

        self.running_time += dt_ms
        frames = dt_ms / MS_PER_FRAME

        if self.jumping:
            self._update_jump(frames)
        elif self.down_held:
            self.ducking = True
        else:
            self.ducking = False

        self.distance_ran += self.current_speed * frames
        if self.current_speed < MAX_SPEED:
            self.current_speed = min(MAX_SPEED, self.current_speed + ACCELERATION * frames)

        self.horizon += self.current_speed * frames
        self._update_obstacles(dt_ms, frames)
        self._maybe_cloud(dt_ms, moving=True)
        self._update_anim(dt_ms)
        self._check_achievement()
        self._check_collisions()

        score = self.score()
        if score > self.high_score:
            self.high_score = score
        self._inverted = (score // INVERT_SCORE) % 2 == 1 and score >= INVERT_SCORE

    def _update_wait(self, dt_ms: float) -> None:
        self.blink_timer += dt_ms
        if self.blink_timer >= 200:
            self.blink_on = not self.blink_on
            self.blink_timer = 0.0 if self.blink_on else float(_rand_int(self.rng, 800, 4000))

    def _update_jump(self, frames: float) -> None:
        if self.speed_drop:
            self.y_pos += round(self.jump_velocity * SPEED_DROP_COEFFICIENT * frames)
        else:
            self.y_pos += round(self.jump_velocity * frames)
        self.jump_velocity += GRAVITY * frames
        min_y = self.ground_y - MIN_JUMP_HEIGHT
        if self.y_pos < min_y or self.speed_drop:
            self.reached_min_height = True
        if self.y_pos < MAX_JUMP_HEIGHT_Y or self.speed_drop:
            self._end_jump()
        if self.y_pos > self.ground_y:
            self.y_pos = self.ground_y
            self.jump_velocity = 0.0
            self.jumping = False
            self.speed_drop = False
            if self.down_held:
                self.ducking = True

    def _update_anim(self, dt_ms: float) -> None:
        period = DUCK_MS_PER_FRAME if self.ducking else RUN_MS_PER_FRAME
        self.anim_timer += dt_ms
        if self.anim_timer >= period:
            self.anim_timer = 0.0
            self.anim_frame = 1 - self.anim_frame

    def _update_obstacles(self, dt_ms: float, frames: float) -> None:
        has_obstacles = self.running_time > CLEAR_TIME_MS
        if not has_obstacles:
            return
        alive: list[Obstacle] = []
        for obst in self.obstacles:
            speed = self.current_speed + obst.speed_offset
            obst.x -= speed * frames
            if obst.kind.num_frames > 1:
                obst.timer += dt_ms
                if obst.timer >= PTERO_MS_PER_FRAME:
                    obst.timer = 0.0
                    obst.frame = (obst.frame + 1) % obst.kind.num_frames
            if obst.visible():
                alive.append(obst)
        self.obstacles = alive
        if self._spawn_frozen:
            return
        if self.obstacles:
            last = self.obstacles[-1]
            if (
                not last.following_created
                and last.visible()
                and (last.x + last.width + last.gap) < self.canvas_width
            ):
                self._add_obstacle()
                last.following_created = True
        else:
            self._add_obstacle()

    def _duplicate(self, key: str) -> bool:
        count = 0
        for prev in self.obstacle_history:
            count = count + 1 if prev == key else 0
        return count >= MAX_OBSTACLE_DUPLICATION

    def _add_obstacle(self) -> None:
        for _ in range(16):
            kind = self.rng.choice(OBSTACLE_TYPES)
            if self._duplicate(kind.key) or self.current_speed < kind.min_speed:
                continue
            size = _rand_int(self.rng, 1, MAX_OBSTACLE_LENGTH)
            if size > 1 and kind.multiple_speed > self.current_speed:
                size = 1
            if kind is PTERODACTYL:
                size = 1
            y = kind.y_pos[_rand_int(self.rng, 0, len(kind.y_pos) - 1)]
            width = kind.width * size
            boxes = list(kind.boxes)
            if size > 1 and len(boxes) >= 3:
                boxes[1] = CollisionBox(
                    boxes[1].x,
                    boxes[1].y,
                    width - boxes[0].w - boxes[2].w,
                    boxes[1].h,
                )
                boxes[2] = CollisionBox(width - boxes[2].w, boxes[2].y, boxes[2].w, boxes[2].h)
            offset = 0.0
            if kind.speed_offset:
                offset = kind.speed_offset if self.rng.random() > 0.5 else -kind.speed_offset
            min_gap = round(width * self.current_speed + kind.min_gap * GAP_COEFFICIENT)
            max_gap = round(min_gap * MAX_GAP_COEFFICIENT)
            gap = _rand_int(self.rng, min_gap, max(min_gap, max_gap))
            self.obstacles.append(
                Obstacle(
                    kind=kind,
                    x=self.canvas_width + kind.width,
                    y=float(y),
                    size=size,
                    gap=float(gap),
                    speed_offset=offset,
                    boxes=tuple(boxes),
                )
            )
            self.obstacle_history.insert(0, kind.key)
            if len(self.obstacle_history) > MAX_OBSTACLE_DUPLICATION:
                self.obstacle_history = self.obstacle_history[:MAX_OBSTACLE_DUPLICATION]
            return

    def _maybe_cloud(self, dt_ms: float, moving: bool) -> None:
        frames = dt_ms / MS_PER_FRAME
        if moving:
            for cloud in self.clouds:
                cloud.x -= CLOUD_SPEED * self.current_speed * frames
            self.clouds = [c for c in self.clouds if c.x > -40]
        if len(self.clouds) < CLOUD_MAX and self.rng.random() < 0.02:
            last_x = max((c.x for c in self.clouds), default=self.canvas_width)
            if last_x < self.canvas_width - 80:
                self.clouds.append(
                    Cloud(
                        x=self.canvas_width,
                        y=float(_rand_int(self.rng, CLOUD_MIN_SKY_Y, CLOUD_MAX_SKY_Y)),
                    )
                )
            elif not self.clouds:
                self.clouds.append(
                    Cloud(
                        x=self.canvas_width * 0.6,
                        y=float(_rand_int(self.rng, CLOUD_MIN_SKY_Y, CLOUD_MAX_SKY_Y)),
                    )
                )

    def _check_collisions(self) -> None:
        for obst in self.obstacles:
            if crashed(
                self.x_pos,
                self.y_pos,
                self.ducking and not self.jumping,
                obst.x,
                obst.y,
                obst.width,
                obst.height,
                obst.boxes,
            ):
                self.crashed = True
                self.jumping = False
                if self.score() > self.high_score:
                    self.high_score = self.score()
                return

    def _check_achievement(self) -> None:
        score = self.score()
        if score > 0 and score % ACHIEVEMENT_DISTANCE == 0:
            self._flash_score = True
            self._flash_timer = 0.0

    def score(self) -> int:
        return int(round(self.distance_ran * SCORE_COEFFICIENT))

    # -- render -----------------------------------------------------------

    def render(self, cols: int, rows: int) -> list[str]:
        cols = max(40, cols)
        rows = max(12, rows)
        hud_rows = 2
        footer_rows = 2
        play_rows = max(10, rows - hud_rows - footer_rows)
        px_row = CANVAS_HEIGHT / play_rows
        # Keep Chrome's 600px world. Stretch it across the terminal so the
        # runway is always full-width; do not mutate physics mid-run.
        px_col = self.canvas_width / cols

        buf = [[" "] * cols for _ in range(play_rows)]
        ground_row = play_rows - 1

        for cloud in self.clouds:
            sprites.blit(buf, sprites.CLOUD, int(cloud.x / px_col), max(0, int(cloud.y / px_row)))

        tiles = sprites.GROUND_TILES
        offset = int(self.horizon / px_col) % len(tiles)
        for x in range(cols):
            buf[ground_row][x] = tiles[(x + offset) % len(tiles)]

        for obst in self.obstacles:
            art = self._obstacle_art(obst)
            self._blit_world(buf, art, obst.x, obst.y, obst.height, px_col, px_row)

        dino_art = self._dino_art()
        # Chrome keeps y_pos as the top of the 47px standing box even when
        # ducking; sit the shorter duck frames on that same baseline.
        self._blit_world(buf, dino_art, self.x_pos, self.y_pos, TREX_HEIGHT, px_col, px_row)

        play = ["".join(row) for row in buf]

        score = self.score()
        score_txt = str(score).zfill(SCORE_DIGITS)
        hi_txt = str(self.high_score).zfill(SCORE_DIGITS)
        if self._flash_score:
            self._flash_timer += 16
            if int(self._flash_timer / 250) % 2 == 0:
                score_txt = " " * SCORE_DIGITS
            if self._flash_timer > 1200:
                self._flash_score = False
        meters = f"HI {hi_txt}  {score_txt}"
        title = "Console · dino"
        hud = title + meters.rjust(max(0, cols - len(title)))
        if len(hud) > cols:
            hud = hud[-cols:]

        banner = ""
        if self._saw_banner:
            banner = self._center("✓ TASK DONE", cols)
        elif self.crashed:
            banner = self._center("G A M E  O V E R", cols)
        elif self.waiting:
            banner = self._center("Press Space to run", cols)
        else:
            banner = " " * cols
        banner = banner[:cols].ljust(cols)

        if self.crashed:
            footer = self._center("Space restart   Esc leave Console", cols)
        elif self._saw_banner:
            footer = self._center("Spawns frozen · Esc wipes this run", cols)
        else:
            footer = self._center("Space/↑ jump   ↓ duck   Esc leave", cols)
        footer = footer[:cols].ljust(cols)

        lines = [hud[:cols].ljust(cols), banner, *play]
        while len(lines) < rows - 1:
            lines.append(" " * cols)
        lines.append(footer)
        return [line[:cols].ljust(cols) for line in lines[:rows]]

    @staticmethod
    def _blit_world(
        buf: list[list[str]],
        art: tuple[str, ...],
        x: float,
        y: float,
        height_px: float,
        px_col: float,
        px_row: float,
    ) -> None:
        col = int(x / px_col)
        bottom = int((y + height_px) / px_row)
        sprites.blit(buf, art, col, bottom - len(art))

    def _dino_art(self) -> tuple[str, ...]:
        if self.crashed:
            return sprites.DINO_DEAD
        if self.waiting:
            return sprites.DINO_BLINK if self.blink_on else sprites.DINO_WAIT
        if self.jumping:
            return sprites.DINO_JUMP
        if self.ducking:
            return sprites.DINO_DUCK_1 if self.anim_frame == 0 else sprites.DINO_DUCK_2
        return sprites.DINO_RUN_1 if self.anim_frame == 0 else sprites.DINO_RUN_2

    def _obstacle_art(self, obst: Obstacle) -> tuple[str, ...]:
        if obst.kind is PTERODACTYL:
            return sprites.PTERO_1 if obst.frame == 0 else sprites.PTERO_2
        unit = sprites.CACTUS_LARGE if obst.kind is CACTUS_LARGE else sprites.CACTUS_SMALL
        if obst.size <= 1:
            return unit
        gap = ""
        merged = []
        width = len(unit[0]) * obst.size + len(gap) * (obst.size - 1)
        for row_parts in zip(*([unit] * obst.size)):
            merged.append(gap.join(row_parts).ljust(width))
        return tuple(merged)

    @staticmethod
    def _center(text: str, cols: int) -> str:
        text = text[:cols]
        pad = max(0, cols - len(text))
        left = pad // 2
        return (" " * left) + text + (" " * (pad - left))


register("dino")(DinoGame)
