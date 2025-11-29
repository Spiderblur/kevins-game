from __future__ import annotations

from dataclasses import dataclass, field

import pygame

import settings


@dataclass
class PlayerState:
    pos: pygame.Vector2
    radius: int
    max_health: int
    health: int
    facing: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(1, 0))
    speed: float = settings.PLAYER_BASE_SPEED
    swing_timer: float = 0.0
    cooldown: float = 0.0
    swing_base_dir: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(1, 0))
    is_blocking: bool = False
    shield_blocks_left: int = settings.SHIELD_MAX_BLOCKS
    is_drinking_potion: bool = False
    potion_timer: float = 0.0
    potion_count: int = settings.START_POTION_COUNT
    knockback_timer: float = 0.0
    knockback_vec: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))


def create_player(start_pos: pygame.Vector2) -> PlayerState:
    return PlayerState(
        pos=start_pos.copy(),
        radius=settings.PLAYER_RADIUS,
        max_health=settings.PLAYER_MAX_HEALTH,
        health=settings.PLAYER_MAX_HEALTH,
    )
