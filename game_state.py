from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pygame

import settings
from player import PlayerState, create_player
from pig import PigState


@dataclass
class GameState:
    screen: pygame.Surface
    clock: pygame.time.Clock
    player: PlayerState
    pigs: List[PigState] = field(default_factory=list)
    running: bool = True
    dt: float = 0.0
    game_over: bool = False
    chase_range: float = settings.CHASE_RANGE
    pig_speed: float = settings.PIG_SPEED
    inventory: list[str] = field(default_factory=lambda: ["" for _ in range(settings.INVENTORY_SLOTS)])
    inventory_open: bool = False
    coin_pickups: list[dict] = field(default_factory=list)
    coin_count: int = 0
    blood_splats: list[dict] = field(default_factory=list)
    shake_timer: float = 0.0
    door_revealed: bool = False
    level_index: int = 3  # start near the shopkeeper
    leather_armor_bought: bool = False
    has_map: bool = False
    map_open: bool = False
    shopkeeper_greeted: bool = False
    map_tested: bool = False
    dialogue_lines: list[str] = field(default_factory=list)
    dialogue_index: int = 0
    dialogue_start_time: float = 0.0
    font: pygame.font.Font | None = None


def create_game_state(screen: pygame.Surface) -> GameState:
    """Initialize the whole game state with defaults."""
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, settings.FONT_SIZE)
    player = create_player(
        pygame.Vector2(settings.SCREEN_WIDTH / 2, settings.SCREEN_HEIGHT / 2)
    )
    state = GameState(screen=screen, clock=clock, player=player, font=font)
    return state
