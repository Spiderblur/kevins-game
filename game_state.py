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
    chests: list[dict] = field(default_factory=list)
    loot_notices: list[dict] = field(default_factory=list)
    shake_timer: float = 0.0
    door_revealed: bool = False
    camera_offset: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
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
    lock_target: PigState | None = None
    auto_open_map_after_dialogue: bool = False
    treasure_hint_visible: bool = False
    quest_explained: bool = False
    intro_active: bool = True
    intro_lines: list[str] = field(default_factory=list)
    intro_durations: list[float] = field(default_factory=list)
    intro_index: int = 0
    intro_line_start: float = 0.0


def create_game_state(screen: pygame.Surface) -> GameState:
    """Initialize the whole game state with defaults."""
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, settings.FONT_SIZE)
    player = create_player(
        pygame.Vector2(settings.SCREEN_WIDTH / 2, settings.SCREEN_HEIGHT / 2)
    )
    state = GameState(screen=screen, clock=clock, player=player, font=font)
    # Intro text sequence shown before waking in the first room
    state.intro_lines = [
        "In the beginning, there was peace.",
        "Until he came and destroyed all.",
        "Please save us.",
        "You are Elrule's last hope.",
    ]
    state.intro_durations = [2.5, 2.5, 2.5, 2.5]
    state.intro_line_start = pygame.time.get_ticks() / 1000.0

    # Debug start: skip intro and begin in the field with progress.
    state.intro_active = False
    state.level_index = settings.FIELD_LEVEL_INDEX
    state.coin_count = 50
    state.has_map = True
    state.shopkeeper_greeted = True
    # Give the player basic gear + bow.
    starter = ["Sword", "Shield", "Bow", "Health Potion"]
    for i, item in enumerate(starter):
        if i < len(state.inventory):
            state.inventory[i] = item
    state.player.weapon_item = "Sword"
    state.player.shield_item = "Shield"
    state.player.bow_equipped = True
    state.player.potion_count = 1
    return state
