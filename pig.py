from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pygame

import settings


@dataclass
class PigState:
    pos: pygame.Vector2
    max_health: int = settings.PIG_MAX_HEALTH
    health: int | None = None
    radius: int = settings.PIG_RADIUS
    facing: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(1, 0))
    swing_timer: float = 0.0
    cooldown: float = 0.0
    attack_cooldown: float = settings.PIG_COOLDOWN
    windup_time: float = settings.PIG_WINDUP_TIME
    swing_time: float = settings.PIG_SWING_TIME
    knockback_timer: float = 0.0
    knockback_vec: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    coin_dropped: bool = False
    swing_base_dir: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(1, 0))
    is_evil: bool = False
    is_boss: bool = False
    in_boss_arena: bool = False
    is_ally: bool = False
    windup_timer: float = 0.0
    walk_cycle: float = 0.0

    def __post_init__(self):
        if self.health is None:
            self.health = int(self.max_health)


def make_pig(
    pos: pygame.Vector2,
    *,
    is_evil: bool = False,
    max_health: int = settings.PIG_MAX_HEALTH,
    radius: int = settings.PIG_RADIUS,
    attack_cooldown: float = settings.PIG_COOLDOWN,
    windup_time: float = settings.PIG_WINDUP_TIME,
    swing_time: float = settings.PIG_SWING_TIME,
    is_boss: bool = False,
    in_boss_arena: bool = False,
    is_ally: bool = False,
) -> PigState:
    return PigState(
        pos=pygame.Vector2(pos),
        is_evil=is_evil,
        max_health=max_health,
        radius=radius,
        attack_cooldown=attack_cooldown,
        windup_time=windup_time,
        swing_time=swing_time,
        is_boss=is_boss,
        in_boss_arena=in_boss_arena,
        is_ally=is_ally,
    )


def spawn_pigs(n: int, level_index: int, screen: pygame.Surface) -> List[PigState]:
    pigs: List[PigState] = []
    spacing = 80
    center_y = screen.get_height() / 2
    start_y = center_y - (spacing * (n - 1) / 2)
    base_x = screen.get_width() / 4
    if level_index >= 3:
        base_x += 220
    for i in range(n):
        y = start_y + i * spacing
        pos = pygame.Vector2(base_x, y)
        pigs.append(make_pig(pos))
    return pigs
