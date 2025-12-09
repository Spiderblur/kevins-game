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
    arrows: list[dict] = field(default_factory=list)
    shake_timer: float = 0.0
    door_revealed: bool = False
    level_index: int = 1
    leather_armor_bought: bool = False
    has_map: bool = False
    map_open: bool = False
    shopkeeper_greeted: bool = False
    map_tested: bool = False
    rumor_shown: bool = False
    evil_spawned: bool = False
    evil_defeated: bool = False
    bow_given: bool = False
    dialogue_lines: list[str] = field(default_factory=list)
    dialogue_index: int = 0
    dialogue_start_time: float = 0.0
    resume_lines: list[str] = field(default_factory=list)
    resume_index: int = 0
    font: pygame.font.Font | None = None
    map_comment_shown: bool = False


def create_game_state(screen: pygame.Surface) -> GameState:
    """Initialize the whole game state with defaults."""
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, settings.FONT_SIZE)
    player = create_player(
        pygame.Vector2(settings.SCREEN_WIDTH / 2, settings.SCREEN_HEIGHT / 2)
    )
    state = GameState(screen=screen, clock=clock, player=player, font=font)
    # Starter gear to demo equipment slots (grouped: armor, weapons, potions)
    starter = [
        # Armor section
        "Explorer Cap",
        "Cloth Tunic",
        "Traveler Pants",
        # Weapons section
        "Sword",
        "Bow",
        # Potions section
        "Health Potion",
    ]
    for i, item in enumerate(starter):
        if i < len(state.inventory):
            state.inventory[i] = item
    # Start at the very beginning of the game (first level)
    state.level_index = 1
    # Start with no coins by default
    state.coin_count = 0
    return state
