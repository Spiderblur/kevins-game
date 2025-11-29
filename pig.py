from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pygame

import settings


@dataclass
class PigState:
    pos: pygame.Vector2
    health: int = settings.PIG_MAX_HEALTH
    facing: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(1, 0))
    swing_timer: float = 0.0
    cooldown: float = 0.0
    knockback_timer: float = 0.0
    knockback_vec: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    coin_dropped: bool = False
    swing_base_dir: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(1, 0))


def make_pig(pos: pygame.Vector2) -> PigState:
    return PigState(pos=pygame.Vector2(pos))


def spawn_pigs(n: int, level_index: int, screen: pygame.Surface) -> List[PigState]:
    pigs: List[PigState] = []
    spacing = 80
    center_y = screen.get_height() / 2
    start_y = center_y - (spacing * (n - 1) / 2)
    base_x = screen.get_width() / 4
    if level_index == 2:
        base_x += 220
    for i in range(n):
        y = start_y + i * spacing
        pos = pygame.Vector2(base_x, y)
        pigs.append(make_pig(pos))
    return pigs
