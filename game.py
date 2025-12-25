import math
import random
import sys
from typing import List

import pygame

import settings
from combat import (
    deal_damage_if_hit,
    get_swing_dir,
    sword_polygon_points,
    swing_ease,
    swing_reach_multiplier,
)
from effects import spawn_blood_splatter
from game_state import GameState, create_game_state
from hud import (
    draw_coin_icon,
    draw_boss_health_bar_bottom,
    draw_health_bar_above,
    draw_player_health_bar_topleft,
    draw_player_stamina_bar_topleft,
    draw_potion_icon,
)
from inventory import (
    add_item_to_inventory,
    apply_equipment_effects,
    draw_inventory_panel,
    ensure_default_equipment,
    equip_item_from_inventory,
    get_inventory_layout,
    get_slot_rect,
    get_grouped_slot_rects,
)
from pig import spawn_pigs, make_pig
from utils import line_of_sight_clear
from world import (
    blit_field_environment,
    get_field_boss_arena_door_rect,
    get_field_boss_arena_rect,
    get_field_boss_arena_wall_rects,
    get_field_farm_rects,
    get_field_house_solid_rects,
    get_field_house_rects,
    get_field_map_surface,
    get_field_pond_rect,
    get_field_ruins_rects,
    get_field_shrine_rect,
    get_room3_table_rect,
    get_shopkeeper_rect,
)

DIALOGUE_BOX_PADDING = 10
DIALOGUE_BUTTON_PADDING = 10
MAP_INTRO_LINE1 = "Shopkeeper: \"You look new. Here's a free map!\""
MAP_INTRO_LINE2 = "Shopkeeper: \"Why don't you try and use it?\""
RUMOR_LINE1 = "Shopkeeper: \"Did you hear the rumor about the possessed creatures?\""
RUMOR_LINE2 = "Shopkeeper: \"Mladlor, the evil king, has been turning good creatures bad.\""
EVIL_LINE = "Shopkeeper: \"Hey, look! There's one right there!\""
THANKS_LINE = "Shopkeeper: \"Wow, you saved my life! Here, take this.\""
POTENTIAL_LINE = "Shopkeeper: \"You have a lot of potential.\""
SKILL_LINE = "Shopkeeper: \"I have never seen someone with your skill.\""
OPEN_MAP_LINE = "Shopkeeper: \"Open the map next.\""
TREASURE_LINE = "Shopkeeper: \"If you go to this point, there might be some loot you can claim.\""
MONSTER_WARN_LINE = "Shopkeeper: \"But beware, there are lots of monsters there.\""
SPIRIT_REWARD_LINE1 = "Spirit: \"Heroic actions must be rewarded. Here is a reward for you.\""
SPIRIT_REWARD_LINE2 = "Spirit: \"I just enhanced your abilities.\""
SPIRIT_WHO_LINE1 = "You: \"Who are you?\""
SPIRIT_WHO_LINE2 = "Spirit: \"Who am I? I'm afraid I have to keep that a secret.\""
SPIRIT_WHO_LINE3 = "Spirit: \"Continue on your journey, and may you always have spirit.\""
POST_BOSS_LINE1 = "Shopkeeper: \"Wow! You did it.\""
POST_BOSS_LINE2 = "Shopkeeper: \"You know, there are a couple of villages that might need your help.\""
POST_BOSS_LINE3 = "Shopkeeper: \"These two villages have been in peril for a long time.\""
POST_BOSS_LINE4 = "Shopkeeper: \"My village is lucky to be safe.\""
POST_BOSS_LINE5 = "Shopkeeper: \"If you go to these places, they'll be grateful forever.\""
ROOM3_FIELD_WIDTH = settings.FIELD_WORLD_WIDTH
ROOM3_FIELD_HEIGHT = settings.FIELD_WORLD_HEIGHT
FIELD_LEVEL = settings.FIELD_LEVEL_INDEX
INTRO_LINE_DURATION = 2.0
LOOT_REVEAL_TIME = 2.5
LEATHER_ARMOR_UNLOCKED = True
ROOM_WORLD_WIDTH = settings.SCREEN_WIDTH * 3
ROOM_WORLD_HEIGHT = settings.SCREEN_HEIGHT * 3
MAP_TO_PERSON_SCALE = 1.0
# Quest location in field world coordinates (far enough to feel like a journey).
QUEST_POS_WORLD = pygame.Vector2(ROOM3_FIELD_WIDTH * 0.85, ROOM3_FIELD_HEIGHT * 0.25)
# Villages are near the edges (for exploration) but not pinned to the very border.
VILLAGE_EDGE_PAD = 1200
# Southwest village: keep it in the bottom-left area, but not stuck on the border.
# Placing it between major landmarks (e.g. shrine and farms) feels more natural.
VILLAGE_SW_POS_WORLD = pygame.Vector2(int(ROOM3_FIELD_WIDTH * 0.30), int(ROOM3_FIELD_HEIGHT * 0.78))
VILLAGE_SE_POS_WORLD = pygame.Vector2(ROOM3_FIELD_WIDTH - VILLAGE_EDGE_PAD, ROOM3_FIELD_HEIGHT - int(VILLAGE_EDGE_PAD * 1.55))


def current_world_size(state: GameState) -> tuple[int, int]:
    if state.level_index == FIELD_LEVEL:
        return ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT
    return ROOM_WORLD_WIDTH, ROOM_WORLD_HEIGHT


def get_door_rect_world(state: GameState) -> pygame.Rect:
    """Door rect in world coordinates (not camera-adjusted)."""
    world_w, world_h = current_world_size(state)
    if state.level_index == 1:
        x = world_w - settings.DOOR_MARGIN - settings.FIRST_ROOM_DOOR_WIDTH
        y = (world_h - settings.FIRST_ROOM_DOOR_HEIGHT) // 2
        return pygame.Rect(x, y, settings.FIRST_ROOM_DOOR_WIDTH, settings.FIRST_ROOM_DOOR_HEIGHT)
    x = world_w - settings.DOOR_MARGIN - settings.DOOR_WIDTH
    y = (world_h - settings.DOOR_HEIGHT) // 2
    return pygame.Rect(x, y, settings.DOOR_WIDTH, settings.DOOR_HEIGHT)


def apply_field_start_progress(state: GameState):
    """Set story flags for starting in the field post-evil fight."""
    state.level_index = FIELD_LEVEL
    state.coin_count = 50
    state.has_map = True
    state.shopkeeper_greeted = True
    state.map_tested = True
    state.rumor_shown = True
    state.evil_spawned = True
    state.evil_defeated = True
    state.bow_given = True
    state.treasure_hint_visible = True
    state.quest_explained = True
    state.pigs = []
    state.boss_spawned = False
    state.boss_defeated = False
    state.boss_door_closed = False
    state.boss_reward_spawned = False
    state.spirit_spawned = False
    state.spirit_reward_given = False
    state.spirit_departed = False
    state.dialogue_tag = None
    update_camera_follow(state)


def apply_post_bow_start(state: GameState, coin_count: int = 10):
    """Dev shortcut: start in the field after receiving the bow (saves early dialogue/combat)."""
    state.coin_count = coin_count
    state.has_map = True
    state.shopkeeper_greeted = True
    state.map_tested = True
    state.rumor_shown = True
    state.evil_spawned = True
    state.evil_defeated = True
    state.bow_given = True
    state.treasure_hint_visible = True
    state.quest_explained = True

    # Ensure the bow exists and is equipped for quick testing.
    if settings.ITEM_OLD_BOW not in state.inventory:
        for i, item in enumerate(state.inventory):
            if item == "":
                state.inventory[i] = settings.ITEM_OLD_BOW
                break
        else:
            state.inventory[-1] = settings.ITEM_OLD_BOW
    state.player.bow_equipped = True


def apply_post_boss_start(state: GameState, coin_count: int = 75):
    """Dev shortcut: start in the field after the pig boss is defeated."""
    state.level_index = FIELD_LEVEL
    state.coin_count = coin_count
    state.has_map = True
    state.shopkeeper_greeted = True
    state.map_tested = True
    state.rumor_shown = True
    state.evil_spawned = True
    state.evil_defeated = True
    state.bow_given = True
    state.quest_explained = True
    state.treasure_hint_visible = False

    # Boss already cleared; prevent re-spawning the encounter.
    allies = [p for p in state.pigs if getattr(p, "is_ally", False) and p.health > 0]
    state.pigs = allies
    state.pending_pig_spawns = []
    spawn_field_roaming_pigs(state, count=35)
    state.boss_spawned = True
    state.boss_defeated = True
    state.boss_door_closed = False
    state.boss_reward_spawned = True
    state.spirit_spawned = True
    state.spirit_reward_given = True
    state.spirit_departed = True
    state.lock_target = None
    state.post_boss_return_to_shopkeeper = True
    state.post_boss_shopkeeper_done = False
    state.villages_revealed = False
    state.quest_lines = ["Quest: Updated - Talk to the shopkeeper"]
    state.quest_markers = [pygame.Vector2(get_shopkeeper_rect(state.screen).center)]

    # Grant post-boss loot and equip it.
    if "Bacon of the Dead" not in state.inventory:
        add_item_to_inventory(state, "Bacon of the Dead")
    state.player.summon_item = "Bacon of the Dead"

    # Ensure the bow exists and is equipped for quick testing.
    if settings.ITEM_OLD_BOW not in state.inventory:
        add_item_to_inventory(state, settings.ITEM_OLD_BOW)
    state.player.bow_equipped = True
    state.player.bow_cooldown = 0.0

    # Apply spirit reward bonus (post-boss).
    state.player.max_health += settings.SPIRIT_HEALTH_BONUS
    state.player.health = state.player.max_health

    # Spawn the player near the boss arena exit.
    door = get_field_boss_arena_door_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT)
    state.player.pos.update(door.centerx, door.bottom + state.player.radius + 90)
    update_camera_follow(state)


def get_spirit_rect_world() -> pygame.Rect:
    """World rect for the post-boss spirit that blocks the boss arena exit."""
    door = get_field_boss_arena_door_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT)
    rect = pygame.Rect(0, 0, settings.NPC_WIDTH, settings.NPC_HEIGHT)
    rect.midbottom = door.midbottom
    return rect


def spawn_boss_reward_chest(state: GameState, pos_world: pygame.Vector2):
    if state.boss_reward_spawned:
        return
    state.boss_reward_spawned = True
    state.chests.append(
        {
            "pos": pygame.Vector2(pos_world),
            "item": "Bacon of the Dead",
            "opened": False,
            "reveal_timer": 0.0,
        }
    )


def handle_boss_defeated(state: GameState, boss_pos: pygame.Vector2):
    """Boss defeat hook: clear arena enemies, spawn reward chest, and spawn spirit gate."""
    if state.boss_defeated:
        return
    state.boss_defeated = True
    state.boss_door_closed = False
    state.lock_target = None

    # Kill all arena pigs (boss + minions) so the room clears out.
    for pig in state.pigs:
        if pig.health <= 0:
            continue
        if getattr(pig, "is_ally", False):
            continue
        if pig.is_boss or getattr(pig, "in_boss_arena", False):
            pig.health = 0
            pig.windup_timer = 0.0
            pig.swing_timer = 0.0
            pig.cooldown = 0.0
            pig.coin_dropped = True

    # Reward chest appears near where the boss died.
    spawn_boss_reward_chest(state, pygame.Vector2(boss_pos) + pygame.Vector2(0, 120))

    # Spirit blocks the exit until you talk to it.
    state.spirit_spawned = True
    state.spirit_reward_given = False
    state.spirit_departed = False

    # Quest update: return to the shopkeeper.
    state.post_boss_return_to_shopkeeper = True
    state.post_boss_shopkeeper_done = False
    state.villages_revealed = False
    state.quest_lines = ["Quest: Updated - Talk to the shopkeeper"]
    state.quest_markers = [pygame.Vector2(get_shopkeeper_rect(state.screen).center)]


def spawn_pig_boss_encounter(state: GameState):
    arena = get_field_boss_arena_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT)
    thickness = 36
    inner = arena.inflate(-thickness * 2 - 80, -thickness * 2 - 80)
    inner.center = arena.center

    boss_pos = pygame.Vector2(inner.centerx, inner.centery - 40)
    boss = make_pig(
        boss_pos,
        max_health=settings.PIG_MAX_HEALTH * 10,
        radius=int(settings.PIG_RADIUS * 1.85),
        windup_time=settings.PIG_WINDUP_TIME * 1.6,
        attack_cooldown=max(1.2, settings.PIG_COOLDOWN + 1.2),
        is_boss=True,
        in_boss_arena=True,
    )

    # Fewer minions so the boss fight is less crowded.
    offsets = [(-180, 100), (180, 100)]
    minions = [
        make_pig(
            pygame.Vector2(boss_pos.x + dx, boss_pos.y + dy),
            in_boss_arena=True,
        )
        for dx, dy in offsets
    ]

    state.pigs.extend([boss, *minions])
    state.boss_spawned = True
    state.boss_door_closed = True


def spawn_field_roaming_pigs(state: GameState, count: int = 35):
    """Generate spawn locations for overworld pigs (spawned when the player is nearby)."""
    if state.level_index != FIELD_LEVEL:
        return
    rng = random.Random(pygame.time.get_ticks())
    arena = get_field_boss_arena_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT).inflate(160, 160)
    pond = get_field_pond_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT).inflate(40, 40)
    farms = [r.inflate(40, 40) for r in get_field_farm_rects(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT)]

    table = get_room3_table_rect(state.screen, pygame.Vector2(0, 0)).inflate(900, 700)
    keeper = get_shopkeeper_rect(state.screen).inflate(900, 700)
    houses = [r.inflate(120, 120) for r in get_field_house_solid_rects(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT)]

    def blocked(x: float, y: float) -> bool:
        if arena.collidepoint(x, y) or pond.collidepoint(x, y):
            return True
        if table.collidepoint(x, y) or keeper.collidepoint(x, y):
            return True
        if any(r.collidepoint(x, y) for r in farms):
            return True
        if any(r.collidepoint(x, y) for r in houses):
            return True
        return False

    spawns: list[pygame.Vector2] = []
    tries = max(200, count * 35)
    for _ in range(tries):
        if len(spawns) >= count:
            break
        x = rng.uniform(settings.PLAYER_RADIUS, ROOM3_FIELD_WIDTH - settings.PLAYER_RADIUS)
        y = rng.uniform(settings.PLAYER_RADIUS, ROOM3_FIELD_HEIGHT - settings.PLAYER_RADIUS)
        if blocked(x, y):
            continue
        spawns.append(pygame.Vector2(x, y))

    state.pending_pig_spawns.extend(spawns)


def spawn_pending_pigs_near_player(state: GameState, view_rect_world: pygame.Rect):
    if state.level_index != FIELD_LEVEL or not state.pending_pig_spawns:
        return
    padding = getattr(settings, "FIELD_PIG_SPAWN_VIEW_PADDING", 900)
    max_per_tick = getattr(settings, "FIELD_PIG_SPAWN_PER_TICK", 4)
    spawn_rect = view_rect_world.inflate(padding * 2, padding * 2)

    player_pos = state.player.pos
    candidates: list[pygame.Vector2] = []
    remaining: list[pygame.Vector2] = []
    for pos in state.pending_pig_spawns:
        if spawn_rect.collidepoint(pos.x, pos.y):
            candidates.append(pos)
        else:
            remaining.append(pos)

    if not candidates:
        state.pending_pig_spawns = remaining
        return

    candidates.sort(key=lambda p: (p - player_pos).length_squared())
    to_spawn = candidates[:max_per_tick]
    leftover = candidates[max_per_tick:]
    for pos in to_spawn:
        state.pigs.append(make_pig(pos))
    state.pending_pig_spawns = remaining + leftover


def sync_bacon_companion(state: GameState):
    """Keep the Bacon of the Dead companion active while equipped, otherwise despawn it."""
    player = state.player
    bacon_equipped = getattr(player, "summon_item", "") == "Bacon of the Dead"
    allies = [p for p in state.pigs if getattr(p, "is_ally", False)]

    if not bacon_equipped:
        if allies:
            state.pigs = [p for p in state.pigs if not getattr(p, "is_ally", False)]
        return

    alive_allies = [p for p in allies if p.health > 0]
    if len(alive_allies) > 1:
        keep = min(alive_allies, key=lambda p: (p.pos - player.pos).length_squared())
        state.pigs = [p for p in state.pigs if (not getattr(p, "is_ally", False)) or p is keep]
        alive_allies = [keep]

    if not alive_allies:
        in_arena = False
        if state.level_index == FIELD_LEVEL:
            arena = get_field_boss_arena_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT)
            in_arena = arena.collidepoint(player.pos.x, player.pos.y)
        ally = make_pig(
            pygame.Vector2(player.pos),
            max_health=int(settings.PIG_MAX_HEALTH * 2),
            radius=int(settings.PIG_RADIUS * 0.9),
            attack_cooldown=0.35,
            windup_time=0.25,
            swing_time=0.35,
            in_boss_arena=in_arena,
            is_ally=True,
        )
        ally.coin_dropped = True
        state.pigs.append(ally)
        return

    ally = alive_allies[0]
    # Companion movement is handled in the main update loop (no teleporting).


def despawn_far_enemies(state: GameState, view_rect_world: pygame.Rect):
    """Despawn non-essential enemies that have been far away for a while (field roamers only)."""
    if not state.pigs:
        return
    player_pos = state.player.pos
    despawn_seconds = float(getattr(settings, "ENEMY_DESPAWN_SECONDS", 10.0))
    range_mult = float(getattr(settings, "ENEMY_DESPAWN_RANGE_MULT", 1.35))
    range_px = float(getattr(settings, "PLAYER_SIGHT_RANGE", 500)) * range_mult
    range_sq = range_px * range_px

    lock = state.lock_target
    keep: list = []
    for pig in state.pigs:
        if pig.health <= 0:
            keep.append(pig)
            continue
        if getattr(pig, "is_ally", False) or getattr(pig, "is_boss", False) or getattr(pig, "in_boss_arena", False) or getattr(pig, "is_evil", False):
            pig.out_of_range_timer = 0.0
            keep.append(pig)
            continue

        dist_sq = (pig.pos - player_pos).length_squared()
        in_view = view_rect_world.collidepoint(pig.pos.x, pig.pos.y)
        if dist_sq <= range_sq or in_view:
            pig.out_of_range_timer = 0.0
            keep.append(pig)
            continue

        pig.out_of_range_timer += state.dt
        if pig.out_of_range_timer < despawn_seconds:
            keep.append(pig)
            continue

        # Despawn: re-add the position as a pending spawn in the field so it can reappear later.
        if state.level_index == FIELD_LEVEL:
            state.pending_pig_spawns.append(pygame.Vector2(pig.pos))

    state.pigs = keep
    if lock is not None and all(p is not lock for p in keep):
        state.lock_target = None


def start_field_intro(state: GameState):
    """Begin the shopkeeper's initial field script (map intro)."""
    if state.level_index != FIELD_LEVEL or state.shopkeeper_greeted:
        return
    state.shopkeeper_greeted = True
    state.has_map = True
    state.treasure_hint_visible = False
    start_dialogue(state, [MAP_INTRO_LINE1, MAP_INTRO_LINE2])


def push_circle_out_of_rect(pos: pygame.Vector2, radius: float, rect: pygame.Rect):
    """Push a circle center out of a rect if overlapping (minimal axis push)."""
    closest_x = max(rect.left, min(pos.x, rect.right))
    closest_y = max(rect.top, min(pos.y, rect.bottom))
    dx = pos.x - closest_x
    dy = pos.y - closest_y
    dist_sq = dx * dx + dy * dy
    if dist_sq == 0:
        # Center is exactly at a corner; push upward by radius
        pos.y = rect.top - radius
        return
    if dist_sq < radius * radius:
        dist = math.sqrt(dist_sq)
        push = radius - dist
        if dist > 0:
            pos.x += dx / dist * push
            pos.y += dy / dist * push


def push_circle_out_of_circle(center: pygame.Vector2, radius: float, other_center: pygame.Vector2, other_radius: float):
    """Push a circle center away from another circle if overlapping."""
    delta = center - other_center
    dist_sq = delta.length_squared()
    min_dist = radius + other_radius
    if dist_sq == 0:
        # Perfect overlap; push upward.
        center.y -= min_dist
        return
    dist = math.sqrt(dist_sq)
    if dist < min_dist:
        push = min_dist - dist
        dir_vec = delta / dist
        center.x += dir_vec.x * push
        center.y += dir_vec.y * push


def clamp_circle_in_rect(center: pygame.Vector2, radius: float, rect: pygame.Rect):
    """Clamp a circle center so the whole circle stays inside rect."""
    center.x = max(rect.left + radius, min(center.x, rect.right - radius))
    center.y = max(rect.top + radius, min(center.y, rect.bottom - radius))


def start_dialogue(state: GameState, lines: List[str], *, tag: str | None = None):
    """Begin showing dialogue lines with typewriter reveal."""
    state.dialogue_lines = list(lines)
    state.dialogue_index = 0
    state.dialogue_start_time = pygame.time.get_ticks() / 1000.0
    state.resume_lines = list(lines)
    state.resume_index = 0
    state.dialogue_tag = tag


def restore_dialogue(state: GameState):
    """Bring back dialogue if it was paused for the map."""
    if state.resume_lines and not state.dialogue_lines:
        state.dialogue_lines = list(state.resume_lines)
        state.dialogue_index = max(0, state.resume_index)
        state.dialogue_start_time = pygame.time.get_ticks() / 1000.0


def spawn_evil_creature(state: GameState):
    """Spawn a single pig-like enemy once when warned."""
    if state.evil_spawned:
        return
    spawn_pos = pygame.Vector2(state.screen.get_width() * 0.75, state.screen.get_height() / 2)
    state.pigs.append(make_pig(spawn_pos, is_evil=True))
    state.evil_spawned = True


def update_camera_follow(state: GameState, margin: int = 140):
    """Keep the player on-screen by moving the camera when near edges."""
    cam = state.camera_offset
    player = state.player
    screen_w, screen_h = state.screen.get_width(), state.screen.get_height()
    world_w, world_h = current_world_size(state)
    zoom = float(getattr(state, "camera_zoom", 1.0))
    if zoom <= 0:
        zoom = 1.0
    view_w = screen_w / zoom
    view_h = screen_h / zoom
    max_x = max(0.0, world_w - view_w)
    max_y = max(0.0, world_h - view_h)
    screen_pos = (player.pos - cam) * zoom

    if screen_pos.x < margin:
        cam.x = player.pos.x - (margin / zoom)
    elif screen_pos.x > screen_w - margin:
        cam.x = player.pos.x - ((screen_w - margin) / zoom)
    cam.x = max(0.0, min(cam.x, max_x))

    if screen_pos.y < margin:
        cam.y = player.pos.y - (margin / zoom)
    elif screen_pos.y > screen_h - margin:
        cam.y = player.pos.y - ((screen_h - margin) / zoom)
    cam.y = max(0.0, min(cam.y, max_y))


def give_bow(state: GameState):
    """Place a bow in the first empty inventory slot (once)."""
    if state.bow_given:
        return
    for i, item in enumerate(state.inventory):
        if item == "":
            state.inventory[i] = settings.ITEM_OLD_BOW
            state.bow_given = True
            return
    # If no empty slots, overwrite last slot
    state.inventory[-1] = settings.ITEM_OLD_BOW
    state.bow_given = True


def draw_item_icon(surface: pygame.Surface, center: pygame.Vector2, item: str, size: int = 32):
    """Small item icon for loot popups/chests."""
    x, y = int(center.x), int(center.y)
    half = size // 2
    if item == settings.ITEM_RUSTY_SWORD:
        pygame.draw.line(surface, (180, 210, 255), (x, y - half), (x, y + half), 4)
        pygame.draw.circle(surface, (80, 50, 30), (x, y + half + 4), 4)
    elif item == settings.ITEM_RUSTY_SHIELD:
        points = [(x - half, y), (x + half, y - half), (x + half, y + half)]
        pygame.draw.polygon(surface, (120, 180, 230), points)
        pygame.draw.polygon(surface, (80, 120, 170), points, 2)
    elif item == settings.ITEM_OLD_BOW:
        cx, cy = x, y
        tri = [
            (cx - 10, cy + 12),
            (cx - 10, cy - 12),
            (cx + 14, cy),
        ]
        pygame.draw.polygon(surface, (200, 200, 255), tri, 0)
    elif item == "Health Potion":
        flask = pygame.Rect(x - half + 6, y - half + 6, size - 12, size - 6)
        pygame.draw.rect(surface, (200, 80, 80), flask, border_radius=4)
        pygame.draw.rect(surface, (240, 200, 200), (flask.x, flask.y, flask.width, 6), border_radius=3)
    elif item in ("Explorer Cap", "Traveler Hood"):
        cap_rect = pygame.Rect(x - half + 4, y - half + 8, size - 8, size - 10)
        pygame.draw.rect(surface, (150, 90, 40), cap_rect, border_radius=6)
    elif item in ("Cloth Tunic", "Leather Armor"):
        body_rect = pygame.Rect(x - half + 6, y - half + 4, size - 12, size - 10)
        color = (170, 110, 70) if "Leather" in item else (130, 100, 160)
        pygame.draw.rect(surface, color, body_rect, border_radius=4)
    elif item in ("Traveler Pants", "Runner Boots"):
        pant_rect = pygame.Rect(x - half + 8, y - half + 4, size - 16, size - 6)
        pygame.draw.rect(surface, (90, 70, 50), pant_rect, border_radius=4)
    else:
        pygame.draw.circle(surface, (220, 220, 220), (x, y), half)


def create_room1_chests(state: GameState) -> list[dict]:
    """Lay out starter chests in the empty first room."""
    world_w, world_h = current_world_size(state)
    items = [
        settings.ITEM_RUSTY_SWORD,
        settings.ITEM_RUSTY_SHIELD,
        "Health Potion",
        "Explorer Cap",
        "Cloth Tunic",
        "Traveler Pants",
    ]
    cols = 4
    spacing = 140
    start_x = world_w / 2 - spacing * (cols - 1) / 2
    start_y = world_h * 0.45
    chests = []
    for idx, item in enumerate(items):
        row = idx // cols
        col = idx % cols
        pos = pygame.Vector2(start_x + col * spacing, start_y + row * spacing)
        chests.append({"pos": pos, "item": item, "opened": False, "reveal_timer": 0.0})
    return chests


def auto_equip_if_empty(state: GameState, item: str):
    """Equip common items immediately if their slot is empty."""
    player = state.player
    if item == settings.ITEM_RUSTY_SWORD and not getattr(player, "weapon_item", ""):
        player.weapon_item = settings.ITEM_RUSTY_SWORD
    elif item == settings.ITEM_RUSTY_SHIELD and not getattr(player, "shield_item", ""):
        player.shield_item = settings.ITEM_RUSTY_SHIELD
    elif item in ("Explorer Cap", "Traveler Hood") and not getattr(player, "head_item", ""):
        player.head_item = item
    elif item in ("Cloth Tunic", "Leather Armor") and not getattr(player, "body_item", ""):
        player.body_item = item
    elif item in ("Traveler Pants", "Runner Boots") and not getattr(player, "legs_item", ""):
        player.legs_item = item
    apply_equipment_effects(player)


def try_open_chest(state: GameState, open_radius: float = 110.0) -> bool:
    """Open the nearest unopened chest when close enough."""
    if not state.chests:
        return False
    player_pos = state.player.pos
    for chest in state.chests:
        if chest.get("opened"):
            continue
        if (player_pos - chest["pos"]).length() <= open_radius:
            chest["opened"] = True
            item = chest["item"]
            chest["reveal_timer"] = LOOT_REVEAL_TIME
            add_item_to_inventory(state, item)
            auto_equip_if_empty(state, item)
            # Health potions also add one ready-to-use charge
            if item == "Health Potion":
                state.player.potion_count += 1
            return True
    return False


def draw_room1_chests(state: GameState, cam: pygame.Vector2, *, surface: pygame.Surface | None = None):
    """Render chests and prompts."""
    if not state.chests:
        return
    screen = surface if surface is not None else state.screen
    font = state.font
    chest_size = 54
    prompt_radius = 140
    for chest in state.chests:
        pos = chest["pos"] - cam
        rect = pygame.Rect(int(pos.x - chest_size / 2), int(pos.y - chest_size / 2), chest_size, chest_size)
        base_color = (130, 90, 50) if not chest["opened"] else (70, 70, 70)
        trim_color = (210, 170, 90) if not chest["opened"] else (160, 160, 160)
        pygame.draw.rect(screen, base_color, rect, border_radius=6)
        pygame.draw.rect(screen, trim_color, rect, 4, border_radius=6)
        latch = pygame.Rect(rect.centerx - 6, rect.centery - 6, 12, 12)
        pygame.draw.rect(screen, trim_color, latch, border_radius=3)
        if not chest["opened"]:
            dist = (state.player.pos - chest["pos"]).length()
            if dist <= prompt_radius and font:
                prompt = font.render("Press E to open", True, (255, 255, 255))
                screen.blit(prompt, (rect.centerx - prompt.get_width() // 2, rect.top - 40))
        else:
            if chest.get("reveal_timer", 0) > 0 and font:
                icon_center = pygame.Vector2(rect.centerx - 30, rect.top - 32)
                draw_item_icon(screen, icon_center, chest["item"], size=28)
                name = font.render(chest["item"], True, (240, 240, 240))
                screen.blit(name, (icon_center.x + 30, icon_center.y - name.get_height() // 2))


def current_dialogue_text(state: GameState):
    if not state.dialogue_lines or state.dialogue_index >= len(state.dialogue_lines):
        return None
    return state.dialogue_lines[state.dialogue_index]


def dialogue_reveal(state: GameState):
    """Return (shown_text, is_full) for current dialogue line."""
    line = current_dialogue_text(state)
    if line is None:
        return "", True
    now = pygame.time.get_ticks() / 1000.0
    elapsed = max(0.0, now - state.dialogue_start_time)
    chars = int(elapsed * settings.DIALOGUE_CHARS_PER_SEC)
    if chars >= len(line):
        return line, True
    return line[:chars], False


def handle_dialogue_click(state: GameState):
    """Advance dialogue: finish reveal or go to next line."""
    line = current_dialogue_text(state)
    if line is None:
        return
    shown, full = dialogue_reveal(state)
    now = pygame.time.get_ticks() / 1000.0
    finished_tag: str | None = None
    if not full:
        # Instantly finish this line
        state.dialogue_start_time = now - (len(line) / settings.DIALOGUE_CHARS_PER_SEC)
        return
    if state.dialogue_index + 1 < len(state.dialogue_lines):
        state.dialogue_index += 1
        state.resume_index = state.dialogue_index
        state.dialogue_start_time = now
    else:
        # Finished this dialogue block; clear active dialogue and resume state
        finished_tag = state.dialogue_tag
        state.dialogue_lines = []
        state.dialogue_index = 0
        state.dialogue_start_time = 0.0
        state.resume_lines = []
        state.resume_index = 0
        state.dialogue_tag = None
        # After map is tested, auto-advance to rumor lines once
    # Spawn evil creature when reaching the warning line (once)
    if line == EVIL_LINE and not state.evil_spawned:
        spawn_evil_creature(state)
    if line == THANKS_LINE:
        give_bow(state)
    if line == MONSTER_WARN_LINE:
        state.quest_explained = True
    if state.dialogue_tag == "post_boss_villages" and state.dialogue_index == 2:
        state.map_open = True
        state.map_tested = True
        state.quest_markers = [VILLAGE_SW_POS_WORLD, VILLAGE_SE_POS_WORLD]
    if finished_tag == "spirit_depart":
        state.spirit_departed = True
    if finished_tag == "post_boss_villages":
        state.post_boss_shopkeeper_done = True
        state.post_boss_return_to_shopkeeper = False
        state.villages_revealed = True
        state.quest_lines = [
            "Quests: Help the villages (press M)",
            "Southwest village",
            "Southeast village",
        ]
        state.quest_markers = [VILLAGE_SW_POS_WORLD, VILLAGE_SE_POS_WORLD]


def draw_dialogue(state: GameState):
    """Draw the current dialogue with a simple typewriter reveal and a prompt button."""
    line = current_dialogue_text(state)
    if line is None or state.font is None:
        return
    shown, full = dialogue_reveal(state)
    screen = state.screen
    text_surf = state.font.render(shown, True, (255, 255, 200))
    box_rect = text_surf.get_rect()
    box_rect.inflate_ip(DIALOGUE_BOX_PADDING * 2, DIALOGUE_BOX_PADDING * 2)
    box_rect.centerx = screen.get_width() // 2
    box_rect.top = 20
    pygame.draw.rect(screen, (30, 30, 60), box_rect)
    pygame.draw.rect(screen, (200, 200, 255), box_rect, 2)
    text_pos = (
        box_rect.centerx - text_surf.get_width() // 2,
        box_rect.top + DIALOGUE_BOX_PADDING,
    )
    screen.blit(text_surf, text_pos)

    # Button-like prompt below the box
    prompt_text = "Click text to continue"
    prompt_surf = state.font.render(prompt_text, True, (255, 255, 255) if full else (180, 180, 180))
    prompt_rect = prompt_surf.get_rect()
    prompt_rect.centerx = box_rect.centerx
    prompt_rect.top = box_rect.bottom + DIALOGUE_BUTTON_PADDING
    back_rect = prompt_rect.inflate(12, 8)
    pygame.draw.rect(screen, (40, 40, 70), back_rect)
    pygame.draw.rect(screen, (150, 150, 200), back_rect, 2)
    screen.blit(prompt_surf, prompt_rect)


def get_active_quest_lines(state: GameState) -> list[str]:
    if state.quest_lines:
        return list(state.quest_lines)
    if state.treasure_hint_visible:
        return ["Quest: Find the treasure", "Open the map (M) to see it"]
    if state.has_map and not state.shopkeeper_greeted:
        return ["Quest: Talk to the shopkeeper"]
    return []


def draw_quests_panel(state: GameState):
    screen = state.screen
    font = state.font or pygame.font.SysFont(None, settings.FONT_SIZE)
    title_font = pygame.font.SysFont(None, 56)

    full = pygame.Rect(0, 0, screen.get_width(), screen.get_height())
    pygame.draw.rect(screen, (18, 20, 30), full)
    pygame.draw.rect(screen, (90, 120, 150), full, 6)

    title = title_font.render("Quests", True, (230, 240, 255))
    screen.blit(title, (24, 20))

    lines = get_active_quest_lines(state)
    if not lines:
        lines = ["No active quests right now."]
    y = 110
    for text in lines[:10]:
        surf = font.render(text, True, (255, 240, 150))
        screen.blit(surf, (28, y))
        y += 34

    hint = font.render("Press Tab to close", True, (180, 200, 220))
    screen.blit(hint, (24, screen.get_height() - 46))


def advance_intro(state: GameState):
    """Move to the next intro line or start the game."""
    state.intro_index += 1
    if state.intro_index >= len(state.intro_lines):
        state.intro_active = False
        state.intro_lines = []
        state.intro_index = 0
        state.intro_line_start = 0.0
        reset_round(state)
        return
    state.intro_line_start = pygame.time.get_ticks() / 1000.0


def update_intro(state: GameState, events: list[pygame.event.Event]):
    """Handle clicks/keys to advance intro text and auto-advance over time."""
    if not state.intro_active:
        return
    for event in events:
        if event.type == pygame.QUIT:
            state.running = False
        elif event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            advance_intro(state)
    now = pygame.time.get_ticks() / 1000.0
    dur_list = state.intro_durations or []
    current_dur = dur_list[state.intro_index] if state.intro_index < len(dur_list) else INTRO_LINE_DURATION
    if now - state.intro_line_start >= current_dur:
        advance_intro(state)


def draw_intro(state: GameState):
    """Draw the black-screen intro text."""
    if not state.intro_active:
        return
    screen = state.screen
    screen.fill((0, 0, 0))
    if not state.font or not state.intro_lines:
        return
    idx = min(state.intro_index, len(state.intro_lines) - 1)
    line = state.intro_lines[idx]
    text_surf = state.font.render(line, True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=(screen.get_width() / 2, screen.get_height() / 2))
    screen.blit(text_surf, text_rect)


def reset_round(state: GameState):
    """Reset positions, health, enemies, and timers for the current level."""
    player = state.player
    player.health = player.max_health
    player.speed = settings.PLAYER_BASE_SPEED
    player.swing_timer = 0.0
    player.swing_recover_timer = 0.0
    player.last_swing_reach = 1.0
    player.cooldown = 0.0
    player.is_blocking = False
    player.shield_blocks_left = settings.SHIELD_MAX_BLOCKS
    player.is_drinking_potion = False
    player.potion_timer = 0.0
    player.is_dodging = False
    player.dodge_timer = 0.0
    player.dodge_cooldown = 0.0
    player.knockback_timer = 0.0
    player.knockback_vec.update(0, 0)
    player.stamina = settings.STAMINA_MAX
    player.stamina_exhausted = False
    player.is_sprinting = False
    ensure_default_equipment(player)
    state.dialogue_lines = []
    state.dialogue_index = 0
    state.dialogue_start_time = 0.0
    state.map_tested = False
    state.rumor_shown = False
    state.evil_spawned = False
    state.evil_defeated = False
    state.bow_given = False
    state.resume_lines = []
    state.resume_index = 0
    state.boss_spawned = False
    state.boss_defeated = False
    state.boss_door_closed = False
    state.quest_lines = []
    state.quest_markers = []
    state.post_boss_return_to_shopkeeper = False
    state.post_boss_shopkeeper_done = False
    state.villages_revealed = False
    state.quests_open = False

    # Start position depends on level
    if state.level_index == FIELD_LEVEL:
        t_rect = get_room3_table_rect(state.screen, pygame.Vector2(0, 0))
        player.pos.update(t_rect.centerx - 80, t_rect.bottom + player.radius)
        # Waystones (fast travel points) for the overworld.
        boss_door = get_field_boss_arena_door_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT)
        state.waystones = [
            {"id": "village", "name": "Village Waystone", "pos": pygame.Vector2(t_rect.centerx, t_rect.bottom + 220)},
            {"id": "boss", "name": "Boss Gate Waystone", "pos": pygame.Vector2(boss_door.centerx, boss_door.bottom + 220)},
        ]
        # Make the shop/village waystone available right away.
        if not hasattr(state, "discovered_waystones") or getattr(state, "discovered_waystones", None) is None:
            state.discovered_waystones = set()
        state.discovered_waystones.add("village")
    else:
        player.pos.update(settings.SCREEN_WIDTH / 2, settings.SCREEN_HEIGHT / 2)
    update_camera_follow(state)

    if state.level_index == FIELD_LEVEL and getattr(state, "auto_start_field_intro", False):
        state.auto_start_field_intro = False
        start_field_intro(state)

    state.coin_pickups.clear()
    state.blood_splats.clear()
    state.arrows.clear()
    state.shake_timer = 0.0
    state.game_over = False
    state.door_revealed = state.level_index == 1
    state.chests = create_room1_chests(state) if state.level_index == 1 else []

    # Spawn pigs for the level
    if state.level_index == 1:
        state.pigs = []
        state.pending_pig_spawns = []
    elif state.level_index == 2:
        n = 1
        state.pigs = spawn_pigs(n, state.level_index, state.screen)
        state.pending_pig_spawns = []
    elif state.level_index == 3:
        n = 2
        state.pigs = spawn_pigs(n, state.level_index, state.screen)
        state.pending_pig_spawns = []
    elif state.level_index == FIELD_LEVEL:
        # Field: roamers everywhere
        state.pigs = []
        state.pending_pig_spawns = []
        spawn_field_roaming_pigs(state, count=35)
    else:
        state.pigs = []
        state.pending_pig_spawns = []


def handle_death_screen(state: GameState, events: list[pygame.event.Event]):
    """Draw and manage the death menu (continue/exit)."""
    for event in events:
        if event.type == pygame.QUIT:
            state.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_c, pygame.K_RETURN, pygame.K_SPACE):
                reset_round(state)
            elif event.key in (pygame.K_ESCAPE, pygame.K_e):
                state.running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Handled after buttons are placed
            pass

    screen = state.screen
    screen.fill((0, 0, 0))
    title_font = pygame.font.SysFont(None, 120)
    menu_font = pygame.font.SysFont(None, 48)
    death_text = title_font.render("YOU DIED!", True, (255, 0, 0))
    death_rect = death_text.get_rect(center=(screen.get_width() / 2, screen.get_height() / 2 - 40))
    cont_text = menu_font.render("Continue", True, (255, 255, 255))
    exit_text = menu_font.render("Exit", True, (255, 255, 255))
    cont_rect = cont_text.get_rect(center=(screen.get_width() / 2, screen.get_height() / 2 + 20))
    exit_rect = exit_text.get_rect(center=(screen.get_width() / 2, screen.get_height() / 2 + 70))

    for event in events:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if cont_rect.collidepoint(event.pos):
                reset_round(state)
            elif exit_rect.collidepoint(event.pos):
                state.running = False

    screen.blit(death_text, death_rect)
    screen.blit(cont_text, cont_rect)
    screen.blit(exit_text, exit_rect)
    pygame.display.flip()
    state.dt = state.clock.tick(settings.TARGET_FPS) / 1000


def handle_events(state: GameState, events: list[pygame.event.Event]):
    player = state.player
    zoom = float(getattr(state, "camera_zoom", 1.0))
    if getattr(state, "quests_open", False):
        for event in events:
            if event.type == pygame.QUIT:
                state.running = False
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_TAB, pygame.K_ESCAPE):
                state.quests_open = False
        return
    if state.map_open:
        screen = state.screen
        full_rect = pygame.Rect(0, 0, screen.get_width(), screen.get_height())
        map_w = int(full_rect.width * 0.985)
        map_h = int(full_rect.height * 0.975)
        map_rect = pygame.Rect(0, 0, map_w, map_h)
        map_rect.center = full_rect.center

        base_scale_x = map_rect.width / ROOM3_FIELD_WIDTH
        base_scale_y = map_rect.height / ROOM3_FIELD_HEIGHT

        def clamp_map_center(center_world: pygame.Vector2, zoom_level: float) -> pygame.Vector2:
            scale_x = base_scale_x * zoom_level
            scale_y = base_scale_y * zoom_level
            half_view_w = (map_rect.width / 2) / max(0.0001, scale_x)
            half_view_h = (map_rect.height / 2) / max(0.0001, scale_y)
            cx_min = ROOM3_FIELD_WIDTH / 2 if half_view_w >= ROOM3_FIELD_WIDTH / 2 else half_view_w
            cx_max = ROOM3_FIELD_WIDTH / 2 if half_view_w >= ROOM3_FIELD_WIDTH / 2 else ROOM3_FIELD_WIDTH - half_view_w
            cy_min = ROOM3_FIELD_HEIGHT / 2 if half_view_h >= ROOM3_FIELD_HEIGHT / 2 else half_view_h
            cy_max = ROOM3_FIELD_HEIGHT / 2 if half_view_h >= ROOM3_FIELD_HEIGHT / 2 else ROOM3_FIELD_HEIGHT - half_view_h
            return pygame.Vector2(
                max(cx_min, min(center_world.x, cx_max)),
                max(cy_min, min(center_world.y, cy_max)),
            )

        def handle_map_click(click_pos: tuple[int, int]):
            # Allow advancing dialogue while the map overlay is up
            if state.dialogue_lines:
                handle_dialogue_click(state)
                return

            if not state.has_map:
                return

            map_zoom = float(getattr(state, "map_zoom", 1.0))
            map_zoom = max(getattr(settings, "MAP_ZOOM_MIN", 1.0), min(map_zoom, getattr(settings, "MAP_ZOOM_MAX", 6.0)))
            scale_x = base_scale_x * map_zoom
            scale_y = base_scale_y * map_zoom
            center = pygame.Vector2(getattr(state, "map_center_world", pygame.Vector2(ROOM3_FIELD_WIDTH / 2, ROOM3_FIELD_HEIGHT / 2)))
            center = clamp_map_center(center, map_zoom)
            state.map_zoom = map_zoom
            state.map_center_world = center

            def world_to_map(pos_world: pygame.Vector2) -> pygame.Vector2:
                return pygame.Vector2(
                    map_rect.centerx + (pos_world.x - center.x) * scale_x,
                    map_rect.centery + (pos_world.y - center.y) * scale_y,
                )

            for ws in getattr(state, "waystones", []):
                ws_id = ws.get("id", "")
                if ws_id and ws_id not in getattr(state, "discovered_waystones", set()):
                    continue
                pos = pygame.Vector2(ws.get("pos", (0, 0)))
                mp = world_to_map(pos)
                if not map_rect.collidepoint(int(mp.x), int(mp.y)):
                    continue
                if (pygame.Vector2(click_pos) - mp).length_squared() <= (18 * 18):
                    state.fast_travel_active = True
                    state.fast_travel_timer = 0.0
                    state.fast_travel_duration = 1.2
                    state.fast_travel_from = pygame.Vector2(player.pos)
                    state.fast_travel_to = pygame.Vector2(pos)
                    state.fast_travel_swapped = False
                    state.map_open = False
                    state.map_dragging = False
                    return

        for event in events:
            if event.type == pygame.QUIT:
                state.running = False
            if event.type == pygame.MOUSEWHEEL:
                old_zoom = float(getattr(state, "map_zoom", 1.0))
                step = float(getattr(settings, "MAP_ZOOM_STEP", 0.2))
                new_zoom = old_zoom + (event.y * step)
                new_zoom = max(getattr(settings, "MAP_ZOOM_MIN", 1.0), min(new_zoom, getattr(settings, "MAP_ZOOM_MAX", 6.0)))
                if new_zoom != old_zoom:
                    mouse_pos = pygame.mouse.get_pos()
                    center = pygame.Vector2(getattr(state, "map_center_world", pygame.Vector2(ROOM3_FIELD_WIDTH / 2, ROOM3_FIELD_HEIGHT / 2)))
                    old_scale_x = base_scale_x * old_zoom
                    old_scale_y = base_scale_y * old_zoom
                    focus_world = center + pygame.Vector2(
                        (mouse_pos[0] - map_rect.centerx) / max(0.0001, old_scale_x),
                        (mouse_pos[1] - map_rect.centery) / max(0.0001, old_scale_y),
                    )
                    new_scale_x = base_scale_x * new_zoom
                    new_scale_y = base_scale_y * new_zoom
                    new_center = focus_world - pygame.Vector2(
                        (mouse_pos[0] - map_rect.centerx) / max(0.0001, new_scale_x),
                        (mouse_pos[1] - map_rect.centery) / max(0.0001, new_scale_y),
                    )
                    state.map_zoom = new_zoom
                    state.map_center_world = clamp_map_center(new_center, new_zoom)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
                # Older pygame: mouse wheel up/down reported as buttons 4/5.
                wheel_dir = 1 if event.button == 4 else -1
                old_zoom = float(getattr(state, "map_zoom", 1.0))
                step = float(getattr(settings, "MAP_ZOOM_STEP", 0.2))
                new_zoom = old_zoom + (wheel_dir * step)
                new_zoom = max(getattr(settings, "MAP_ZOOM_MIN", 1.0), min(new_zoom, getattr(settings, "MAP_ZOOM_MAX", 6.0)))
                if new_zoom != old_zoom:
                    mouse_pos = getattr(event, "pos", pygame.mouse.get_pos())
                    center = pygame.Vector2(getattr(state, "map_center_world", pygame.Vector2(ROOM3_FIELD_WIDTH / 2, ROOM3_FIELD_HEIGHT / 2)))
                    old_scale_x = base_scale_x * old_zoom
                    old_scale_y = base_scale_y * old_zoom
                    focus_world = center + pygame.Vector2(
                        (mouse_pos[0] - map_rect.centerx) / max(0.0001, old_scale_x),
                        (mouse_pos[1] - map_rect.centery) / max(0.0001, old_scale_y),
                    )
                    new_scale_x = base_scale_x * new_zoom
                    new_scale_y = base_scale_y * new_zoom
                    new_center = focus_world - pygame.Vector2(
                        (mouse_pos[0] - map_rect.centerx) / max(0.0001, new_scale_x),
                        (mouse_pos[1] - map_rect.centery) / max(0.0001, new_scale_y),
                    )
                    state.map_zoom = new_zoom
                    state.map_center_world = clamp_map_center(new_center, new_zoom)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                map_zoom = float(getattr(state, "map_zoom", 1.0))
                if map_zoom > 1.001 and map_rect.collidepoint(getattr(event, "pos", pygame.mouse.get_pos())):
                    state.map_dragging = True
                    pos = pygame.Vector2(getattr(event, "pos", pygame.mouse.get_pos()))
                    state.map_drag_start = pos
                    state.map_drag_last = pos
                    state.map_drag_moved = False
            if event.type == pygame.MOUSEMOTION and getattr(state, "map_dragging", False):
                zoom_level = float(getattr(state, "map_zoom", 1.0))
                if zoom_level <= 1.001:
                    continue
                pos = pygame.Vector2(getattr(event, "pos", pygame.mouse.get_pos()))
                # Only begin panning once the mouse has moved a bit (so clicks still work).
                if not getattr(state, "map_drag_moved", False):
                    total = pos - pygame.Vector2(getattr(state, "map_drag_start", pos))
                    if total.length_squared() < (6 * 6):
                        continue
                    state.map_drag_moved = True
                    state.map_drag_last = pygame.Vector2(getattr(state, "map_drag_start", pos))

                scale_x = base_scale_x * zoom_level
                scale_y = base_scale_y * zoom_level
                last = pygame.Vector2(getattr(state, "map_drag_last", pos))
                delta = pos - last
                state.map_drag_last = pos
                center = pygame.Vector2(getattr(state, "map_center_world", pygame.Vector2(ROOM3_FIELD_WIDTH / 2, ROOM3_FIELD_HEIGHT / 2)))
                new_center = center - pygame.Vector2(
                    delta.x / max(0.0001, scale_x),
                    delta.y / max(0.0001, scale_y),
                )
                state.map_center_world = clamp_map_center(new_center, zoom_level)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                released_pos = getattr(event, "pos", pygame.mouse.get_pos())
                was_dragging = bool(getattr(state, "map_dragging", False))
                moved = bool(getattr(state, "map_drag_moved", False))
                state.map_dragging = False
                state.map_drag_moved = False
                if was_dragging and moved:
                    continue
                handle_map_click(released_pos)
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_m, pygame.K_ESCAPE):
                state.map_open = False
                state.map_dragging = False
                state.map_drag_moved = False
                restore_dialogue(state)
        return
    for event in events:
        if event.type == pygame.QUIT:
            state.running = False
        if event.type == pygame.MOUSEWHEEL and not getattr(state, "inventory_open", False):
            old = float(getattr(state, "camera_zoom", 1.0))
            step = float(getattr(settings, "CAMERA_ZOOM_STEP", 0.1))
            new_zoom = old + (event.y * step)
            new_zoom = max(getattr(settings, "CAMERA_ZOOM_MIN", 0.6), min(new_zoom, getattr(settings, "CAMERA_ZOOM_MAX", 1.6)))
            if new_zoom != old:
                screen_w, screen_h = state.screen.get_width(), state.screen.get_height()
                center_world = state.camera_offset + pygame.Vector2(screen_w / (2 * old), screen_h / (2 * old))
                state.camera_zoom = new_zoom
                state.camera_offset = center_world - pygame.Vector2(screen_w / (2 * new_zoom), screen_h / (2 * new_zoom))
                update_camera_follow(state)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if state.dialogue_lines:
                handle_dialogue_click(state)
                continue
            if state.level_index >= FIELD_LEVEL:
                npc_rect_world = get_shopkeeper_rect(state.screen)
                world_click = state.camera_offset + pygame.Vector2(event.pos[0] / zoom, event.pos[1] / zoom)
                if npc_rect_world.collidepoint(world_click.x, world_click.y):
                    if state.resume_lines and not state.dialogue_lines:
                        # Resume where the player left off in the shopkeeper script
                        state.dialogue_lines = list(state.resume_lines)
                        if state.resume_lines:
                            state.dialogue_index = min(state.resume_index, len(state.resume_lines) - 1)
                        else:
                            state.dialogue_index = 0
                        state.dialogue_start_time = pygame.time.get_ticks() / 1000.0
                        return
                    if state.post_boss_return_to_shopkeeper and not state.post_boss_shopkeeper_done:
                        state.post_boss_return_to_shopkeeper = False
                        state.quest_markers = []
                        start_dialogue(
                            state,
                            [
                                POST_BOSS_LINE1,
                                POST_BOSS_LINE2,
                                POST_BOSS_LINE3,
                                POST_BOSS_LINE4,
                                POST_BOSS_LINE5,
                            ],
                            tag="post_boss_villages",
                        )
                        return
                    if not state.shopkeeper_greeted:
                        state.shopkeeper_greeted = True
                        state.has_map = True
                        state.treasure_hint_visible = False
                        start_dialogue(
                            state,
                            [
                                MAP_INTRO_LINE1,
                                MAP_INTRO_LINE2,
                            ],
                        )
                        return
                    if not state.map_tested:
                        # Remind player to try the map until they've opened it
                        start_dialogue(
                            state,
                            [
                                MAP_INTRO_LINE1,
                                MAP_INTRO_LINE2,
                            ],
                        )
                        return
                    if state.map_tested and state.shopkeeper_greeted and not state.rumor_shown:
                        state.rumor_shown = True
                        start_dialogue(
                            state,
                            [
                                RUMOR_LINE1,
                                RUMOR_LINE2,
                                EVIL_LINE,
                            ],
                        )
                        return
                    if state.evil_spawned and not state.evil_defeated:
                        start_dialogue(
                            state,
                            [
                                "Shopkeeper: \"Take down that beast first, then come talk to me!\"",
                            ],
                        )
                        return
                    if state.evil_defeated and not state.bow_given:
                        state.treasure_hint_visible = True
                        start_dialogue(
                            state,
                            [
                                THANKS_LINE,
                                POTENTIAL_LINE,
                                SKILL_LINE,
                                OPEN_MAP_LINE,
                                TREASURE_LINE,
                                MONSTER_WARN_LINE,
                            ],
                        )
                        return
                    if state.quest_explained and state.treasure_hint_visible:
                        start_dialogue(
                            state,
                            [
                                "Shopkeeper: \"Go to the point on your map. There will be treasure waiting for you.\"",
                            ],
                        )
                        return
            # Left-click does sword swing; Shift+left-click fires the bow.
            if player.health > 0 and not player.is_drinking_potion:
                mods = pygame.key.get_mods()
                is_shift_held = mods & pygame.KMOD_SHIFT
                if is_shift_held and player.bow_equipped and player.bow_cooldown <= 0:
                    # Ctrl+left-click fires the bow
                    dir_vec = pygame.Vector2(player.facing)
                    if dir_vec.length_squared() == 0:
                        dir_vec = pygame.Vector2(1, 0)
                    dir_vec = dir_vec.normalize()
                    spawn_pos = player.pos + dir_vec * (settings.PLAYER_RADIUS + 10)
                    state.arrows.append({
                        "pos": spawn_pos,
                        "dir": dir_vec,
                    })
                    player.bow_cooldown = settings.BOW_COOLDOWN
                elif not is_shift_held and player.cooldown <= 0 and player.swing_timer <= 0:
                    # Left-click does sword swing
                    player.swing_timer = settings.PLAYER_SWING_TIME
                    player.swing_recover_timer = 0.0
                    player.cooldown = settings.PLAYER_COOLDOWN
                    player.is_blocking = False  # Stop blocking when attacking
                    if player.facing.length_squared() > 0:
                        player.swing_base_dir = player.facing.normalize()
                    else:
                        player.swing_base_dir = pygame.Vector2(1, 0)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            # Only start blocking if the player has a shield equipped
            if (
                player.health > 0
                and getattr(player, "shield_item", "") == settings.ITEM_RUSTY_SHIELD
            ):
                player.is_blocking = True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            player.is_blocking = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            if not getattr(state, "inventory_open", False) and not state.map_open:
                state.quests_open = not getattr(state, "quests_open", False)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_l:
            # Toggle lock-on to nearest living pig
            if state.lock_target and state.lock_target.health > 0 and not getattr(state.lock_target, "is_ally", False):
                state.lock_target = None
            else:
                live_pigs = [p for p in state.pigs if p.health > 0 and not getattr(p, "is_ally", False)]
                if live_pigs:
                    state.lock_target = min(live_pigs, key=lambda p: (p.pos - player.pos).length_squared())
        if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
            if (
                player.potion_count > 0
                and player.health > 0
                and player.health < player.max_health
                and not player.is_drinking_potion
            ):
                player.is_drinking_potion = True
                player.potion_timer = 1.0
        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            if try_open_chest(state):
                continue
            if state.level_index == FIELD_LEVEL and state.spirit_spawned and not state.spirit_departed:
                spirit_rect = get_spirit_rect_world()
                if spirit_rect.inflate(160, 160).collidepoint(player.pos.x, player.pos.y):
                    if not state.spirit_reward_given:
                        state.spirit_reward_given = True
                        player.max_health += settings.SPIRIT_HEALTH_BONUS
                        player.health = min(player.max_health, player.health + settings.SPIRIT_HEALTH_BONUS)
                        start_dialogue(state, [SPIRIT_REWARD_LINE1, SPIRIT_REWARD_LINE2])
                    else:
                        start_dialogue(state, [SPIRIT_WHO_LINE1, SPIRIT_WHO_LINE2, SPIRIT_WHO_LINE3], tag="spirit_depart")
                    continue
            # Waystones: discover when near and pressing E.
            for ws in getattr(state, "waystones", []):
                ws_id = ws.get("id", "")
                ws_pos = pygame.Vector2(ws.get("pos", (0, 0)))
                if (player.pos - ws_pos).length() <= getattr(settings, "WAYSTONE_DISCOVER_RADIUS", 140):
                    if ws_id and ws_id not in getattr(state, "discovered_waystones", set()):
                        state.discovered_waystones.add(ws_id)
                        state.toast_text = "Waystone has been discovered"
                        state.toast_timer = 2.2
                    break
            if (
                LEATHER_ARMOR_UNLOCKED
                and state.level_index >= FIELD_LEVEL
                and not state.leather_armor_bought
            ):
                t_rect = get_room3_table_rect(state.screen, pygame.Vector2(0, 0))
                # Allow purchasing while standing just outside the solid table
                near_rect = t_rect.inflate(settings.PLAYER_RADIUS * 4, settings.PLAYER_RADIUS * 4)
                if near_rect.collidepoint(player.pos.x, player.pos.y) and state.coin_count >= settings.SPEED_POTION_COST:
                    state.coin_count -= settings.SPEED_POTION_COST
                    state.leather_armor_bought = True
                    add_item_to_inventory(state, "Leather Armor")
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            pass
        if state.inventory_open and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_x, mouse_y = event.pos
            grouped = get_grouped_slot_rects(state)
            rects = grouped["rects"]
            buttons = grouped["buttons"]

            handled = False
            # Check action buttons first
            for (i, btn_rect, action) in buttons:
                if btn_rect.collidepoint(mouse_x, mouse_y):
                    item = state.inventory[i]
                    if action == "use_potion":
                        if item == "Speed Potion":
                            player.speed = int(settings.PLAYER_BASE_SPEED * settings.SPEED_BOOST_MULT)
                            state.inventory[i] = ""
                        elif item == "Health Potion":
                            player.potion_count += 1
                            state.inventory[i] = ""
                    elif action == "equip":
                        equip_item_from_inventory(state, i)
                    handled = True
                    break

            if handled:
                continue

            # Only buttons trigger actions; clicking on item text does nothing
        if event.type == pygame.KEYDOWN and event.key == pygame.K_t:
            state.inventory_open = not state.inventory_open
        # Use Shift key to dodge (press)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
            start_dodge(state)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_j:
            if player.bow_equipped and player.bow_cooldown <= 0 and player.health > 0:
                dir_vec = pygame.Vector2(player.facing)
                if dir_vec.length_squared() == 0:
                    dir_vec = pygame.Vector2(1, 0)
                dir_vec = dir_vec.normalize()
                spawn_pos = player.pos + dir_vec * (settings.PLAYER_RADIUS + 10)
                state.arrows.append(
                    {
                        "pos": spawn_pos,
                        "dir": dir_vec,
                    }
                )
                player.bow_cooldown = settings.BOW_COOLDOWN
        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            if state.has_map:
                state.map_open = not state.map_open
                if state.map_open:
                    state.map_tested = True
                else:
                    restore_dialogue(state)


def start_dodge(state: GameState):
    """Start a quick dodge if ready, using the movement input direction when available."""
    player = state.player
    if player.health <= 0 or player.is_dodging or player.dodge_cooldown > 0:
        return
    keys = pygame.key.get_pressed()
    move = pygame.Vector2(0, 0)
    if keys[pygame.K_w]:
        move.y -= 1
    if keys[pygame.K_s]:
        move.y += 1
    if keys[pygame.K_a]:
        move.x -= 1
    if keys[pygame.K_d]:
        move.x += 1
    if move.length_squared() == 0:
        dir_vec = pygame.Vector2(player.facing)
        if dir_vec.length_squared() == 0:
            dir_vec = pygame.Vector2(1, 0)
    else:
        dir_vec = move.normalize()
    player.dodge_dir = dir_vec
    player.is_dodging = True
    player.dodge_timer = settings.DODGE_DURATION
    player.dodge_cooldown = settings.DODGE_COOLDOWN


def update_game(state: GameState):
    player = state.player
    keys = pygame.key.get_pressed()
    # Freeze world updates while the map or inventory is open so the player
    # and enemies can't move or attack while managing inventory/map.
    for chest in state.chests:
        if chest.get("reveal_timer", 0) > 0:
            chest["reveal_timer"] = max(0.0, chest["reveal_timer"] - state.dt)

    if getattr(state, "toast_timer", 0.0) > 0:
        state.toast_timer = max(0.0, state.toast_timer - state.dt)
        if state.toast_timer == 0:
            state.toast_text = ""

    if getattr(state, "fast_travel_active", False):
        state.fast_travel_timer += state.dt
        t = state.fast_travel_timer
        dur = max(0.001, float(getattr(state, "fast_travel_duration", 1.2)))
        if (not getattr(state, "fast_travel_swapped", False)) and t >= dur * 0.5:
            state.player.pos = pygame.Vector2(getattr(state, "fast_travel_to", player.pos))
            state.fast_travel_swapped = True
            update_camera_follow(state)
        if t >= dur:
            state.fast_travel_active = False
            state.fast_travel_timer = 0.0
        return

    if state.map_open or getattr(state, "inventory_open", False) or getattr(state, "quests_open", False):
        return
    if player.health > 0:
        move = pygame.Vector2(0, 0)
        if keys[pygame.K_w]:
            move.y -= 1
        if keys[pygame.K_s]:
            move.y += 1
        if keys[pygame.K_a]:
            move.x -= 1
        if keys[pygame.K_d]:
            move.x += 1
        move_input = pygame.Vector2(move)
        if player.is_dodging:
            player.pos += player.dodge_dir * player.speed * settings.DODGE_SPEED_MULT * state.dt
            player.dodge_timer -= state.dt
            if player.dodge_timer <= 0:
                player.is_dodging = False
        else:
            if move.length_squared() > 0:
                move = move.normalize()
                # Hold Space to sprint
                can_sprint = (not getattr(player, "stamina_exhausted", False)) and player.stamina > 0
                sprinting = keys[pygame.K_SPACE] and can_sprint
                player.is_sprinting = sprinting and move.length_squared() > 0
                speed_mult = settings.SPRINT_SPEED_MULT if player.is_sprinting else 1.0
                player.pos += move * player.speed * speed_mult * state.dt

        if player.knockback_timer > 0:
            player.pos += player.knockback_vec * (settings.KNOCKBACK_SPEED * state.dt)
            player.knockback_timer -= state.dt

        # Prevent walking through the table in the field (level 4)
        if state.level_index == FIELD_LEVEL:
            table_rect = get_room3_table_rect(state.screen, pygame.Vector2(0, 0))
            push_circle_out_of_rect(player.pos, settings.PLAYER_RADIUS, table_rect)
            # Shopkeeper is also solid
            keeper_rect = get_shopkeeper_rect(state.screen)
            push_circle_out_of_rect(player.pos, settings.PLAYER_RADIUS, keeper_rect)
            for house_rect in get_field_house_solid_rects(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT):
                push_circle_out_of_rect(player.pos, settings.PLAYER_RADIUS, house_rect)

            for wall_rect in get_field_boss_arena_wall_rects(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT):
                push_circle_out_of_rect(player.pos, settings.PLAYER_RADIUS, wall_rect)
            if getattr(state, "boss_door_closed", False):
                push_circle_out_of_rect(
                    player.pos,
                    settings.PLAYER_RADIUS,
                    get_field_boss_arena_door_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT),
                )
            if state.spirit_spawned and not state.spirit_departed:
                # Block the arena exit until the spirit departs.
                push_circle_out_of_rect(
                    player.pos,
                    settings.PLAYER_RADIUS,
                    get_field_boss_arena_door_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT),
                )
                push_circle_out_of_rect(player.pos, settings.PLAYER_RADIUS, get_spirit_rect_world())

        # Keep player inside the current world's bounds so they can't walk off-screen.
        world_w, world_h = current_world_size(state)
        player.pos.x = max(settings.PLAYER_RADIUS, min(player.pos.x, world_w - settings.PLAYER_RADIUS))
        player.pos.y = max(settings.PLAYER_RADIUS, min(player.pos.y, world_h - settings.PLAYER_RADIUS))

        if state.level_index == FIELD_LEVEL:
            arena = get_field_boss_arena_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT)
            if arena.collidepoint(player.pos.x, player.pos.y) and not getattr(state, "boss_spawned", False):
                spawn_pig_boss_encounter(state)
            # If the boss door is closed, keep the player inside the arena interior so they can't clip out.
            if getattr(state, "boss_door_closed", False):
                thickness = 36
                arena_inner = arena.inflate(-thickness * 2, -thickness * 2)
                clamp_circle_in_rect(player.pos, settings.PLAYER_RADIUS, arena_inner)

        # Facing: lock-on target (Tab) or last movement direction.
        lock = state.lock_target if state.lock_target and state.lock_target.health > 0 else None
        if lock is None:
            state.lock_target = None
            if player.is_dodging and player.dodge_dir.length_squared() > 0:
                player.facing = pygame.Vector2(player.dodge_dir).normalize()
            elif move_input.length_squared() > 0:
                target_facing = move_input.normalize()
                # Smooth interpolation for reduced jitter (25% move towards target per frame).
                player.facing = player.facing.lerp(target_facing, 0.25)
        else:
            to_target = lock.pos - player.pos
            if to_target.length_squared() > 0:
                player.facing = to_target.normalize()
        update_camera_follow(state)
        if player.swing_timer > 0:
            player.last_attack_dir = get_swing_dir(
                player.swing_base_dir,
                player.swing_timer,
                settings.PLAYER_SWING_TIME,
                player.facing,
            )

    arena_walls: list[pygame.Rect] = []
    arena_door = pygame.Rect(0, 0, 0, 0)
    boss_door_closed = False
    arena_inner: pygame.Rect | None = None
    field_table_rect: pygame.Rect | None = None
    field_keeper_rect: pygame.Rect | None = None
    field_house_solids: list[pygame.Rect] = []
    if state.level_index == FIELD_LEVEL:
        arena_walls = get_field_boss_arena_wall_rects(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT)
        arena_door = get_field_boss_arena_door_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT)
        boss_door_closed = getattr(state, "boss_door_closed", False)
        field_table_rect = get_room3_table_rect(state.screen, pygame.Vector2(0, 0))
        field_keeper_rect = get_shopkeeper_rect(state.screen)
        field_house_solids = get_field_house_solid_rects(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT)
        if boss_door_closed:
            thickness = 36
            arena = get_field_boss_arena_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT)
            arena_inner = arena.inflate(-thickness * 2, -thickness * 2)

    view_rect_world = pygame.Rect(
        int(state.camera_offset.x),
        int(state.camera_offset.y),
        int(state.screen.get_width() / float(getattr(state, "camera_zoom", 1.0))),
        int(state.screen.get_height() / float(getattr(state, "camera_zoom", 1.0))),
    )

    sight_blockers: list[pygame.Rect] = []
    npc_exclusion_rects: list[pygame.Rect] = []
    if state.level_index == FIELD_LEVEL:
        if field_table_rect is not None:
            sight_blockers.append(field_table_rect)
        if field_keeper_rect is not None:
            sight_blockers.append(field_keeper_rect)
        sight_blockers.extend(field_house_solids)
        sight_blockers.extend(arena_walls)
        if boss_door_closed or (state.spirit_spawned and not state.spirit_departed):
            sight_blockers.append(arena_door)
        if state.spirit_spawned and not state.spirit_departed:
            sight_blockers.append(get_spirit_rect_world())
        safe_pad = getattr(settings, "NPC_ENEMY_EXCLUSION_PADDING", 240)
        if field_table_rect is not None:
            npc_exclusion_rects.append(field_table_rect.inflate(safe_pad * 2, safe_pad * 2))
        if field_keeper_rect is not None:
            npc_exclusion_rects.append(field_keeper_rect.inflate(safe_pad * 2, safe_pad * 2))
        if state.spirit_spawned and not state.spirit_departed:
            npc_exclusion_rects.append(get_spirit_rect_world().inflate(safe_pad * 2, safe_pad * 2))

    spawn_pending_pigs_near_player(state, view_rect_world)
    sync_bacon_companion(state)
    despawn_far_enemies(state, view_rect_world)

    for pig in state.pigs:
        if pig.health <= 0:
            continue
        if getattr(pig, "is_ally", False):
            to_player_for_leash = player.pos - pig.pos
            dist_to_player = to_player_for_leash.length()
            return_dist = getattr(settings, "ALLY_RETURN_DISTANCE", 520)
            targets = [
                p
                for p in state.pigs
                if p.health > 0
                and not getattr(p, "is_ally", False)
                and view_rect_world.collidepoint(p.pos.x, p.pos.y)
            ]
            # If the companion falls far behind, ignore enemies and catch up first.
            if dist_to_player > return_dist:
                targets = []
            if targets:
                target = min(targets, key=lambda t: (t.pos - pig.pos).length_squared())
                to_target = target.pos - pig.pos
                dist = to_target.length()
                if dist > 0:
                    pig.facing = to_target / dist
                in_attack_range = dist < (pig.radius + target.radius + settings.SWORD_LENGTH * 0.6)
                ready_to_attack = pig.cooldown <= 0 and pig.swing_timer <= 0 and pig.windup_timer <= 0
                if dist > 0 and pig.windup_timer <= 0 and pig.swing_timer <= 0:
                    move_step = pig.facing * settings.ALLY_PIG_SPEED * state.dt
                    pig.pos += move_step
                    pig.walk_cycle = (pig.walk_cycle + move_step.length() * 0.05) % (math.tau)
                if in_attack_range and ready_to_attack:
                    pig.windup_timer = pig.windup_time
                    pig.swing_base_dir = pig.facing.copy()
            else:
                to_player = player.pos - pig.pos
                dist = to_player.length()
                if dist > 0:
                    pig.facing = to_player / dist
                follow_dist = getattr(settings, "ALLY_FOLLOW_DISTANCE", 90)
                if dist > follow_dist and pig.windup_timer <= 0 and pig.swing_timer <= 0:
                    move_step = pig.facing * settings.ALLY_PIG_SPEED * state.dt
                    pig.pos += move_step
                    pig.walk_cycle = (pig.walk_cycle + move_step.length() * 0.05) % (math.tau)
        else:
            to_player = player.pos - pig.pos
            dist = to_player.length()
            can_player_see_pig = view_rect_world.collidepoint(pig.pos.x, pig.pos.y)

            can_see_player = (
                can_player_see_pig
                and dist < state.chase_range
                and line_of_sight_clear(pig.pos, player.pos, sight_blockers)
            )
            if can_see_player and dist > 0:
                pig.facing = to_player / dist

            in_attack_range = dist < (pig.radius + settings.PLAYER_RADIUS + settings.SWORD_LENGTH * 0.6)
            ready_to_attack = pig.cooldown <= 0 and pig.swing_timer <= 0 and pig.windup_timer <= 0

            if can_see_player and dist > 0 and pig.windup_timer <= 0 and pig.swing_timer <= 0:
                move_step = pig.facing * state.pig_speed * state.dt
                pig.pos += move_step
                pig.walk_cycle = (pig.walk_cycle + move_step.length() * 0.05) % (math.tau)
            if can_see_player and in_attack_range and ready_to_attack:
                pig.windup_timer = pig.windup_time
                pig.swing_base_dir = pig.facing.copy()

        if pig.knockback_timer > 0:
            pig.pos += pig.knockback_vec * (settings.KNOCKBACK_SPEED * state.dt)
            pig.knockback_timer -= state.dt

        if state.level_index == FIELD_LEVEL and pig.in_boss_arena:
            for wall_rect in arena_walls:
                push_circle_out_of_rect(pig.pos, pig.radius, wall_rect)
            if boss_door_closed:
                push_circle_out_of_rect(pig.pos, pig.radius, arena_door)
            if boss_door_closed and arena_inner is not None:
                clamp_circle_in_rect(pig.pos, pig.radius, arena_inner)

    # Prevent pigs from overlapping/squishing together (simple circle separation).
    live_pigs = [p for p in state.pigs if p.health > 0]
    if len(live_pigs) > 1:
        # A couple passes makes the separation feel much more stable.
        for _ in range(2):
            for i in range(len(live_pigs)):
                a = live_pigs[i]
                for j in range(i + 1, len(live_pigs)):
                    b = live_pigs[j]
                    delta = b.pos - a.pos
                    dist_sq = delta.length_squared()
                    min_dist = a.radius + b.radius + 6
                    if dist_sq == 0:
                        # Perfect overlap: pick a direction deterministically from indices.
                        delta = pygame.Vector2(1, 0).rotate((i * 97 + j * 193) % 360)
                        dist_sq = 1.0
                    dist = math.sqrt(dist_sq)
                    if dist < min_dist:
                        push = (min_dist - dist) / 2.0
                        dir_vec = delta / dist
                        a.pos -= dir_vec * push
                        b.pos += dir_vec * push

            # Keep pigs inside bounds and re-apply boss arena walls after separation.
            world_w, world_h = current_world_size(state)
            for pig in live_pigs:
                pig.pos.x = max(pig.radius, min(pig.pos.x, world_w - pig.radius))
                pig.pos.y = max(pig.radius, min(pig.pos.y, world_h - pig.radius))
                if state.level_index == FIELD_LEVEL:
                    if field_table_rect is not None:
                        push_circle_out_of_rect(pig.pos, pig.radius, field_table_rect)
                    if field_keeper_rect is not None:
                        push_circle_out_of_rect(pig.pos, pig.radius, field_keeper_rect)
                    for house_rect in field_house_solids:
                        push_circle_out_of_rect(pig.pos, pig.radius, house_rect)
                    for wall_rect in arena_walls:
                        push_circle_out_of_rect(pig.pos, pig.radius, wall_rect)
                    if boss_door_closed or (state.spirit_spawned and not state.spirit_departed):
                        push_circle_out_of_rect(pig.pos, pig.radius, arena_door)
                    if boss_door_closed and pig.in_boss_arena and arena_inner is not None:
                        clamp_circle_in_rect(pig.pos, pig.radius, arena_inner)
                    if not getattr(pig, "is_ally", False) and npc_exclusion_rects:
                        for safe_rect in npc_exclusion_rects:
                            push_circle_out_of_rect(pig.pos, pig.radius, safe_rect)

    # Keep field pigs out of major solids (table/shop/houses/arena walls).
    if state.level_index == FIELD_LEVEL and live_pigs:
        for pig in live_pigs:
            if field_table_rect is not None:
                push_circle_out_of_rect(pig.pos, pig.radius, field_table_rect)
            if field_keeper_rect is not None:
                push_circle_out_of_rect(pig.pos, pig.radius, field_keeper_rect)
            for house_rect in field_house_solids:
                push_circle_out_of_rect(pig.pos, pig.radius, house_rect)
            for wall_rect in arena_walls:
                push_circle_out_of_rect(pig.pos, pig.radius, wall_rect)
            if boss_door_closed or (state.spirit_spawned and not state.spirit_departed):
                push_circle_out_of_rect(pig.pos, pig.radius, arena_door)
            if boss_door_closed and pig.in_boss_arena and arena_inner is not None:
                clamp_circle_in_rect(pig.pos, pig.radius, arena_inner)
            if not getattr(pig, "is_ally", False) and npc_exclusion_rects:
                for safe_rect in npc_exclusion_rects:
                    push_circle_out_of_rect(pig.pos, pig.radius, safe_rect)

    # Treat pigs as solid so the player can't overlap them.
    if player.health > 0 and live_pigs:
        for pig in live_pigs:
            push_circle_out_of_circle(player.pos, settings.PLAYER_RADIUS, pig.pos, pig.radius)
        world_w, world_h = current_world_size(state)
        player.pos.x = max(settings.PLAYER_RADIUS, min(player.pos.x, world_w - settings.PLAYER_RADIUS))
        player.pos.y = max(settings.PLAYER_RADIUS, min(player.pos.y, world_h - settings.PLAYER_RADIUS))
        if state.level_index == FIELD_LEVEL:
            table_rect = get_room3_table_rect(state.screen, pygame.Vector2(0, 0))
            push_circle_out_of_rect(player.pos, settings.PLAYER_RADIUS, table_rect)
            keeper_rect = get_shopkeeper_rect(state.screen)
            push_circle_out_of_rect(player.pos, settings.PLAYER_RADIUS, keeper_rect)
            for house_rect in get_field_house_solid_rects(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT):
                push_circle_out_of_rect(player.pos, settings.PLAYER_RADIUS, house_rect)
            for wall_rect in get_field_boss_arena_wall_rects(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT):
                push_circle_out_of_rect(player.pos, settings.PLAYER_RADIUS, wall_rect)
            if getattr(state, "boss_door_closed", False):
                push_circle_out_of_rect(
                    player.pos,
                    settings.PLAYER_RADIUS,
                    get_field_boss_arena_door_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT),
                )
                thickness = 36
                arena = get_field_boss_arena_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT)
                arena_inner = arena.inflate(-thickness * 2, -thickness * 2)
                clamp_circle_in_rect(player.pos, settings.PLAYER_RADIUS, arena_inner)
            if state.spirit_spawned and not state.spirit_departed:
                push_circle_out_of_rect(
                    player.pos,
                    settings.PLAYER_RADIUS,
                    get_field_boss_arena_door_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT),
                )
                push_circle_out_of_rect(player.pos, settings.PLAYER_RADIUS, get_spirit_rect_world())

    if player.swing_timer > 0:
        prev_swing = player.swing_timer
        player.swing_timer -= state.dt
        if prev_swing > 0 and player.swing_timer <= 0:
            player.swing_timer = 0
            player.swing_recover_timer = settings.PLAYER_SWING_RECOVER_TIME
    if player.cooldown > 0:
        player.cooldown -= state.dt
    
    # Re-enable shield if right-click is held and swing is done
    keys = pygame.key.get_pressed()
    mouse_buttons = pygame.mouse.get_pressed()
    if mouse_buttons[2]:  # Right mouse button (index 2)
        if player.health > 0 and player.swing_timer <= 0:
            player.is_blocking = True
    if player.bow_cooldown > 0:
        player.bow_cooldown -= state.dt
        if player.bow_cooldown < 0:
            player.bow_cooldown = 0

    for pig in state.pigs:
        if pig.windup_timer > 0:
            pig.windup_timer -= state.dt
            if pig.windup_timer <= 0:
                pig.windup_timer = 0
                pig.swing_timer = pig.swing_time
                pig.swing_base_dir = pig.facing.copy()
        if pig.swing_timer > 0:
            prev = pig.swing_timer
            pig.swing_timer -= state.dt
            if pig.swing_timer < 0:
                pig.swing_timer = 0
            if prev > 0 and pig.swing_timer <= 0:
                pig.cooldown = pig.attack_cooldown
        if pig.cooldown > 0:
            pig.cooldown -= state.dt
            if pig.cooldown < 0:
                pig.cooldown = 0

    if player.is_drinking_potion:
        player.potion_timer -= state.dt
        if player.potion_timer <= 0:
            player.health = min(player.max_health, player.health + settings.POTION_HEAL)
            player.potion_count -= 1
            player.is_drinking_potion = False
    # Stamina drain/regeneration
    if getattr(player, "is_sprinting", False) and player.stamina > 0:
        player.stamina = max(0.0, player.stamina - settings.STAMINA_USE_RATE * state.dt)
        if player.stamina == 0:
            player.is_sprinting = False
            player.stamina_exhausted = True
    elif player.stamina < settings.STAMINA_MAX and not getattr(player, "is_sprinting", False):
        player.stamina = min(settings.STAMINA_MAX, player.stamina + settings.STAMINA_REGEN_RATE * state.dt)
        if player.stamina >= settings.STAMINA_MAX:
            player.stamina_exhausted = False
    if player.dodge_cooldown > 0:
        player.dodge_cooldown -= state.dt
        if player.dodge_cooldown < 0:
            player.dodge_cooldown = 0
    if player.swing_recover_timer > 0:
        player.swing_recover_timer = max(0.0, player.swing_recover_timer - state.dt)

    if state.shake_timer > 0:
        state.shake_timer -= state.dt
        if state.shake_timer < 0:
            state.shake_timer = 0

    # Move arrows and apply damage
    if state.arrows:
        remaining_arrows = []
        for arrow in state.arrows:
            arrow["pos"] = arrow["pos"] + arrow["dir"] * (settings.BOW_SPEED * state.dt)
            pos = arrow["pos"]
            if not (0 <= pos.x <= state.screen.get_width() and 0 <= pos.y <= state.screen.get_height()):
                continue
            hit = False
            for pig in state.pigs:
                if pig.health <= 0:
                    continue
                if getattr(pig, "is_ally", False):
                    continue
                if (pig.pos - pos).length() <= pig.radius:
                    pig.health = max(0, pig.health - settings.BOW_DAMAGE)
                    if pig.health == 0:
                        if pig.is_boss:
                            handle_boss_defeated(state, pig.pos)
                        elif not pig.coin_dropped:
                            state.coin_pickups.append({"pos": pig.pos.copy(), "value": settings.COIN_VALUE})
                            pig.coin_dropped = True
                    hit = True
                    break
            if not hit:
                remaining_arrows.append(arrow)
        state.arrows = remaining_arrows

    if state.blood_splats:
        keep = []
        for s in state.blood_splats:
            s["timer"] -= state.dt
            if s["timer"] > 0:
                keep.append(s)
        state.blood_splats = keep

    if player.health > 0:
        for pig in state.pigs:
            if pig.health <= 0:
                continue
            if getattr(pig, "is_ally", False):
                continue
            player_attack_dir = (
                get_swing_dir(player.swing_base_dir, player.swing_timer, settings.PLAYER_SWING_TIME, player.facing)
                if player.swing_timer > 0
                else player.facing
            )
            if player.swing_timer > 0:
                player.last_attack_dir = pygame.Vector2(player_attack_dir)
            dmg_to_pig = deal_damage_if_hit(
                player.pos,
                player_attack_dir,
                pig.pos,
                pig.radius,
                player.swing_timer,
                settings.PLAYER_SWING_TIME,
                settings.PLAYER_DAMAGE,
                settings.PLAYER_SWING_DISTANCE,
                settings.SWORD_LENGTH,
                settings.SWORD_WIDTH,
            )
            if dmg_to_pig:
                pig.health = max(0, pig.health - dmg_to_pig)
                # Cancel any active attack when knocked back
                pig.windup_timer = 0.0
                pig.swing_timer = 0.0
                pig.cooldown = pig.attack_cooldown
                player.swing_timer = 0
                player.swing_recover_timer = settings.PLAYER_SWING_RECOVER_TIME
                dir_vec = pig.pos - player.pos
                if dir_vec.length_squared() > 0:
                    pig.knockback_vec = dir_vec.normalize()
                    pig.knockback_timer = settings.KNOCKBACK_DURATION
                state.shake_timer = max(state.shake_timer, settings.SHAKE_DURATION)
                spawn_blood_splatter(pig.pos, state.blood_splats)
                if pig.health == 0 and not pig.coin_dropped:
                    state.coin_pickups.append({"pos": pig.pos.copy(), "value": settings.COIN_VALUE})
                    pig.coin_dropped = True
                if pig.health == 0 and pig.is_boss:
                    handle_boss_defeated(state, pig.pos)
                if pig.is_evil and not state.evil_defeated:
                    state.evil_defeated = True

        if state.level_index < FIELD_LEVEL:
            if state.pigs and not state.door_revealed and all(p.health <= 0 for p in state.pigs):
                state.door_revealed = True
        else:
            state.door_revealed = False

    # Ally summon attacks nearby enemies (within the player's view).
    for ally in state.pigs:
        if ally.health <= 0 or not getattr(ally, "is_ally", False):
            continue
        targets = [
            p
            for p in state.pigs
            if p.health > 0
            and not getattr(p, "is_ally", False)
            and view_rect_world.collidepoint(p.pos.x, p.pos.y)
        ]
        if not targets:
            continue
        target = min(targets, key=lambda t: (t.pos - ally.pos).length_squared())
        ally_attack_dir = (
            get_swing_dir(ally.swing_base_dir, ally.swing_timer, ally.swing_time, ally.facing)
            if ally.swing_timer > 0
            else ally.facing
        )
        dmg_to_enemy = deal_damage_if_hit(
            ally.pos,
            ally_attack_dir,
            target.pos,
            target.radius,
            ally.swing_timer,
            ally.swing_time,
            settings.ALLY_PIG_DAMAGE,
            settings.PIG_SWING_DISTANCE,
            settings.SWORD_LENGTH,
            settings.SWORD_WIDTH,
        )
        if dmg_to_enemy:
            target.health = max(0, target.health - dmg_to_enemy)
            # Stop this swing after a successful hit.
            ally.swing_timer = 0.0
            ally.cooldown = ally.attack_cooldown
            # Cancel enemy attack when hit.
            target.windup_timer = 0.0
            target.swing_timer = 0.0
            target.cooldown = target.attack_cooldown
            dir_vec = target.pos - ally.pos
            if dir_vec.length_squared() > 0:
                target.knockback_vec = dir_vec.normalize()
                target.knockback_timer = settings.KNOCKBACK_DURATION
            spawn_blood_splatter(target.pos, state.blood_splats)
            if target.health == 0:
                if target.is_boss:
                    handle_boss_defeated(state, target.pos)
                elif not target.coin_dropped:
                    state.coin_pickups.append({"pos": target.pos.copy(), "value": settings.COIN_VALUE})
                    target.coin_dropped = True

    if player.health > 0:
        for pig in state.pigs:
            if pig.health <= 0:
                continue
            if getattr(pig, "is_ally", False):
                continue
            pig_attack_dir = (
                get_swing_dir(pig.swing_base_dir, pig.swing_timer, pig.swing_time, pig.facing)
                if pig.swing_timer > 0
                else pig.facing
            )
            dmg_to_player = deal_damage_if_hit(
                pig.pos,
                pig_attack_dir,
                player.pos,
                settings.PLAYER_RADIUS,
                pig.swing_timer,
                pig.swing_time,
                settings.PIG_DAMAGE,
                settings.PIG_SWING_DISTANCE,
                settings.SWORD_LENGTH,
                settings.SWORD_WIDTH,
            )
            if dmg_to_player:
                if player.is_dodging:
                    dmg_to_player = 0
                elif player.is_blocking and player.swing_timer <= 0:
                    # Shield blocks when not attacking; no durability drain for now
                    dmg_to_player = 0
                else:
                    if player.armor_equipped:
                        dmg_to_player = int(dmg_to_player * 0.95)
                    player.health = max(0, player.health - dmg_to_player)
                    pig.swing_timer = 0
                    pig.cooldown = pig.attack_cooldown
                    dir_vec = player.pos - pig.pos
                    if dir_vec.length_squared() > 0:
                        player.knockback_vec = dir_vec.normalize()
                        player.knockback_timer = settings.KNOCKBACK_DURATION
                    state.shake_timer = max(state.shake_timer, settings.SHAKE_DURATION)
                    spawn_blood_splatter(player.pos, state.blood_splats)
                    if player.health == 0:
                        player.is_blocking = False
                        state.game_over = True

    if state.coin_pickups and player.health > 0:
        remaining = []
        for coin in state.coin_pickups:
            if (player.pos - coin["pos"]).length() <= settings.COIN_PICKUP_RADIUS:
                state.coin_count += coin["value"]
            else:
                remaining.append(coin)
        state.coin_pickups = remaining

    if state.door_revealed and player.health > 0:
        door = get_door_rect_world(state)
        enter_rect = door.inflate(settings.PLAYER_RADIUS * 2, settings.PLAYER_RADIUS * 2)
        if enter_rect.collidepoint(player.pos.x, player.pos.y):
            state.level_index += 1
            reset_round(state)
            state.door_revealed = False
            player.pos.update(settings.PLAYER_RADIUS + 20, state.screen.get_height() / 2)


def draw_game(state: GameState):
    real_screen = state.screen
    player = state.player
    keys = pygame.key.get_pressed()
    cam = state.camera_offset
    zoom = float(getattr(state, "camera_zoom", 1.0))
    if zoom <= 0:
        zoom = 1.0

    if getattr(state, "quests_open", False):
        draw_quests_panel(state)
        return

    if state.map_open and state.has_map:
        # Draw map overlay on the real screen (not zoomed).
        screen = real_screen
        full_rect = pygame.Rect(0, 0, screen.get_width(), screen.get_height())
        pygame.draw.rect(screen, (28, 34, 48), full_rect)  # dark but not gloomy
        pygame.draw.rect(screen, (90, 120, 150), full_rect, 6)

        map_w = int(full_rect.width * 0.985)
        map_h = int(full_rect.height * 0.975)
        map_rect = pygame.Rect(0, 0, map_w, map_h)
        map_rect.center = full_rect.center
        pygame.draw.rect(screen, (40, 52, 70), map_rect, border_radius=12)

        map_zoom = float(getattr(state, "map_zoom", 1.0))
        map_zoom = max(getattr(settings, "MAP_ZOOM_MIN", 1.0), min(map_zoom, getattr(settings, "MAP_ZOOM_MAX", 6.0)))
        base_scale_x = map_rect.width / ROOM3_FIELD_WIDTH
        base_scale_y = map_rect.height / ROOM3_FIELD_HEIGHT

        def clamp_map_center(center_world: pygame.Vector2, zoom_level: float) -> pygame.Vector2:
            scale_x = base_scale_x * zoom_level
            scale_y = base_scale_y * zoom_level
            half_view_w = (map_rect.width / 2) / max(0.0001, scale_x)
            half_view_h = (map_rect.height / 2) / max(0.0001, scale_y)
            cx_min = ROOM3_FIELD_WIDTH / 2 if half_view_w >= ROOM3_FIELD_WIDTH / 2 else half_view_w
            cx_max = ROOM3_FIELD_WIDTH / 2 if half_view_w >= ROOM3_FIELD_WIDTH / 2 else ROOM3_FIELD_WIDTH - half_view_w
            cy_min = ROOM3_FIELD_HEIGHT / 2 if half_view_h >= ROOM3_FIELD_HEIGHT / 2 else half_view_h
            cy_max = ROOM3_FIELD_HEIGHT / 2 if half_view_h >= ROOM3_FIELD_HEIGHT / 2 else ROOM3_FIELD_HEIGHT - half_view_h
            return pygame.Vector2(
                max(cx_min, min(center_world.x, cx_max)),
                max(cy_min, min(center_world.y, cy_max)),
            )

        center_world = pygame.Vector2(
            getattr(state, "map_center_world", pygame.Vector2(ROOM3_FIELD_WIDTH / 2, ROOM3_FIELD_HEIGHT / 2))
        )
        center_world = clamp_map_center(center_world, map_zoom)
        state.map_zoom = map_zoom
        state.map_center_world = center_world

        scale_x = base_scale_x * map_zoom
        scale_y = base_scale_y * map_zoom

        def world_to_map(pos_world: pygame.Vector2) -> pygame.Vector2:
            return pygame.Vector2(
                map_rect.centerx + (pos_world.x - center_world.x) * scale_x,
                map_rect.centery + (pos_world.y - center_world.y) * scale_y,
            )

        def clamp_map(pos: pygame.Vector2, pad: int = 16) -> pygame.Vector2:
            inner = map_rect.inflate(-pad * 2, -pad * 2)
            return pygame.Vector2(
                max(inner.left, min(pos.x, inner.right)),
                max(inner.top, min(pos.y, inner.bottom)),
            )

        def world_rect_to_map(rect_world: pygame.Rect) -> pygame.Rect:
            tl = world_to_map(pygame.Vector2(rect_world.left, rect_world.top))
            w = max(1, int(rect_world.width * scale_x))
            h = max(1, int(rect_world.height * scale_y))
            return pygame.Rect(int(tl.x), int(tl.y), w, h)

        placed_markers: list[tuple[pygame.Vector2, float]] = []

        def place_marker(pos: pygame.Vector2, radius: float) -> pygame.Vector2 | None:
            if not map_rect.collidepoint(int(pos.x), int(pos.y)):
                return None

            for _ in range(24):
                ok = True
                for other_pos, other_r in placed_markers:
                    if (pos - other_pos).length_squared() < (radius + other_r + 3) ** 2:
                        ok = False
                        break
                if ok:
                    placed_markers.append((pygame.Vector2(pos), float(radius)))
                    return pos

                # Nudge in a small spiral to avoid overlaps (screen-space pixels).
                idx = len(placed_markers) + 1
                ang = idx * 1.7
                step = 6 + (idx % 4) * 3
                pos = pos + pygame.Vector2(math.cos(ang), math.sin(ang)) * step
                if not map_rect.collidepoint(int(pos.x), int(pos.y)):
                    return None

            return None

        # Map background + details clipped to the map area (so zoom/pan doesn't paint outside).
        prev_clip = screen.get_clip()
        screen.set_clip(map_rect)
        env_base = get_field_map_surface((map_rect.width, map_rect.height), ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT)
        if abs(map_zoom - 1.0) < 0.001:
            env_map = env_base
        else:
            env_map = pygame.transform.smoothscale(
                env_base,
                (max(1, int(map_rect.width * map_zoom)), max(1, int(map_rect.height * map_zoom))),
            )
        origin = pygame.Vector2(
            map_rect.centerx - center_world.x * scale_x,
            map_rect.centery - center_world.y * scale_y,
        )
        screen.blit(env_map, (int(origin.x), int(origin.y)))

        # No grid lines: keep the map looking natural.

        arena_rect = world_rect_to_map(get_field_boss_arena_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT))
        pygame.draw.rect(screen, (255, 120, 120), arena_rect, 3, border_radius=10)
        pond_rect = world_rect_to_map(get_field_pond_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT))
        pygame.draw.ellipse(screen, (110, 190, 255), pond_rect, 3)
        for farm in get_field_farm_rects(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT):
            pygame.draw.rect(screen, (120, 240, 150), world_rect_to_map(farm), 3, border_radius=8)
        for house in get_field_house_rects(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT):
            pygame.draw.rect(screen, (240, 220, 180), world_rect_to_map(house), 2, border_radius=6)
        for rr in get_field_ruins_rects(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT):
            pygame.draw.rect(screen, (200, 200, 220), world_rect_to_map(rr), 2, border_radius=10)
        shrine = world_rect_to_map(get_field_shrine_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT))
        pygame.draw.rect(screen, (210, 190, 255), shrine, 3, border_radius=10)

        table = get_room3_table_rect(state.screen, pygame.Vector2(0, 0))
        pygame.draw.rect(screen, (255, 220, 80), world_rect_to_map(table), 3, border_radius=8)
        # Reserve marker space near the shop so quest/waystone dots don't overlap it.
        _shop_anchor = place_marker(world_to_map(pygame.Vector2(table.centerx, table.centery)), radius=12)

        # Waystones on map (clickable if discovered).
        for ws in getattr(state, "waystones", []):
            pos_world = pygame.Vector2(ws.get("pos", (0, 0)))
            ws_id = ws.get("id", "")
            discovered = (not ws_id) or (ws_id in getattr(state, "discovered_waystones", set()))
            mp_raw = world_to_map(pos_world)
            if abs(map_zoom - 1.0) < 0.001:
                mp = clamp_map(mp_raw, pad=16)
            else:
                if not map_rect.collidepoint(int(mp_raw.x), int(mp_raw.y)):
                    continue
                mp = mp_raw
            col = (80, 170, 255) if discovered else (80, 90, 110)
            placed = place_marker(pygame.Vector2(mp), radius=9)
            if placed is None:
                continue
            pygame.draw.circle(screen, col, (int(placed.x), int(placed.y)), 8)
            pygame.draw.circle(screen, (20, 30, 50), (int(placed.x), int(placed.y)), 8, 2)

        # Player arrow icon (only draw when in view; no edge-clamping "dot").
        arrow_color = (255, 220, 80)
        px = max(0, min(player.pos.x, ROOM3_FIELD_WIDTH))
        py = max(0, min(player.pos.y, ROOM3_FIELD_HEIGHT))
        arrow_pos = world_to_map(pygame.Vector2(px, py))
        if not map_rect.collidepoint(int(arrow_pos.x), int(arrow_pos.y)):
            arrow_pos = None
        tip = 10
        half = 7
        if arrow_pos is not None:
            pygame.draw.polygon(
                screen,
                arrow_color,
                [
                    (int(arrow_pos.x), int(arrow_pos.y - tip)),
                    (int(arrow_pos.x - half), int(arrow_pos.y + half)),
                    (int(arrow_pos.x + half), int(arrow_pos.y + half)),
                ],
            )
            pygame.draw.polygon(
                screen,
                (40, 30, 10),
                [
                    (int(arrow_pos.x), int(arrow_pos.y - tip)),
                    (int(arrow_pos.x - half), int(arrow_pos.y + half)),
                    (int(arrow_pos.x + half), int(arrow_pos.y + half)),
                ],
                2,
            )

        markers = state.quest_markers
        if markers:
            quest_fill = (255, 220, 80)
            quest_outline = (255, 255, 120)
            for pos_world in markers[:6]:
                qx = max(0, min(pos_world.x, ROOM3_FIELD_WIDTH))
                qy = max(0, min(pos_world.y, ROOM3_FIELD_HEIGHT))
                quest_pos = world_to_map(pygame.Vector2(qx, qy))
                placed = place_marker(pygame.Vector2(quest_pos), radius=10)
                if placed is None:
                    continue
                pygame.draw.circle(screen, quest_fill, (int(placed.x), int(placed.y)), 8)
                pygame.draw.circle(screen, quest_outline, (int(placed.x), int(placed.y)), 8, 2)
        elif state.treasure_hint_visible:
            qx = max(0, min(QUEST_POS_WORLD.x, ROOM3_FIELD_WIDTH))
            qy = max(0, min(QUEST_POS_WORLD.y, ROOM3_FIELD_HEIGHT))
            quest_pos = world_to_map(pygame.Vector2(qx, qy))
            quest_fill = (255, 220, 80)
            quest_outline = (255, 255, 120)
            placed = place_marker(pygame.Vector2(quest_pos), radius=10)
            if placed is not None:
                pygame.draw.circle(screen, quest_fill, (int(placed.x), int(placed.y)), 8)
                pygame.draw.circle(screen, quest_outline, (int(placed.x), int(placed.y)), 8, 2)

        screen.set_clip(prev_clip)
        pygame.draw.rect(screen, (120, 150, 190), map_rect, 3, border_radius=12)

        ztxt = state.font.render(f"{map_zoom:.1f}x", True, (180, 200, 220))
        screen.blit(ztxt, (map_rect.right - ztxt.get_width() - 16, map_rect.top + 16))
        hint = state.font.render("Wheel: zoom   Left-drag: pan   M: close", True, (180, 200, 220))
        screen.blit(hint, (map_rect.left + 12, map_rect.bottom - 32))
        return

    view_w = max(1, int(real_screen.get_width() / zoom))
    view_h = max(1, int(real_screen.get_height() / zoom))
    screen = pygame.Surface((view_w, view_h))

    if state.level_index != FIELD_LEVEL:
        bg_gray = (120, 120, 120)
        screen.fill(bg_gray)
        rock_color = (100, 100, 100)
        rock_highlight = (180, 180, 180)
        room_w, room_h = current_world_size(state)
        rock_positions = [
            (room_w * 0.2, room_h * 0.7),
            (room_w * 0.5, room_h * 0.3),
            (room_w * 0.8, room_h * 0.6),
        ]
        for rx, ry in rock_positions:
            center = pygame.Vector2(rx, ry) - cam
            pygame.draw.circle(screen, rock_color, (int(center.x), int(center.y)), 36)
            pygame.draw.circle(screen, rock_highlight, (int(center.x - 12), int(center.y - 14)), 10)
        if state.level_index == 1:
            draw_room1_chests(state, cam, surface=screen)
    else:
        blit_field_environment(screen, cam, ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT)
        draw_room1_chests(state, cam, surface=screen)

        table_color = (150, 100, 40)
        table_outline = (90, 60, 20)
        leg_color = (120, 80, 35)
        leg_w, leg_h = 10, 36
        t_rect_world = get_room3_table_rect(real_screen, pygame.Vector2(0, 0))
        t_rect = t_rect_world.move(int(-cam.x), int(-cam.y))
        pygame.draw.rect(screen, table_color, t_rect)
        pygame.draw.rect(screen, table_outline, t_rect, 2)
        legs = [
            pygame.Rect(t_rect.left + 12, t_rect.bottom, leg_w, leg_h),
            pygame.Rect(t_rect.right - 12 - leg_w, t_rect.bottom, leg_w, leg_h),
            pygame.Rect(t_rect.left + 12, t_rect.bottom + leg_h + 2, leg_w, 2),
            pygame.Rect(t_rect.right - 12 - leg_w, t_rect.bottom + leg_h + 2, leg_w, 2),
        ]
        for lr in legs:
            pygame.draw.rect(screen, leg_color, lr)

        # Shopkeeper behind the table
        npc_rect_world = get_shopkeeper_rect(real_screen)
        npc_rect = npc_rect_world.move(int(-cam.x), int(-cam.y))
        pygame.draw.rect(screen, (90, 60, 20), npc_rect)
        pygame.draw.rect(screen, (70, 40, 10), npc_rect, 2)
        head_center = (npc_rect.centerx, npc_rect.top + 12)
        pygame.draw.circle(screen, (240, 210, 180), head_center, 10)
        prompt = state.font.render('Click on me to talk', True, (255, 255, 200))
        screen.blit(prompt, (npc_rect.centerx - prompt.get_width() // 2, npc_rect.top - 26))

        # Waystones (stepping-stone circles)
        for ws in getattr(state, "waystones", []):
            pos = pygame.Vector2(ws.get("pos", (0, 0))) - cam
            ws_id = ws.get("id", "")
            discovered = (not ws_id) or (ws_id in getattr(state, "discovered_waystones", set()))
            r = int(getattr(settings, "WAYSTONE_RADIUS", 34))
            base = (130, 140, 150) if discovered else (80, 90, 100)
            pygame.draw.circle(screen, base, (int(pos.x), int(pos.y)), r)
            pygame.draw.circle(screen, (40, 50, 60), (int(pos.x), int(pos.y)), r, 4)
            pygame.draw.circle(screen, (180, 200, 220), (int(pos.x), int(pos.y)), max(6, r // 5), 2)
            if discovered and (player.pos - pygame.Vector2(ws.get("pos", (0, 0)))).length() <= getattr(settings, "WAYSTONE_DISCOVER_RADIUS", 140):
                if state.font:
                    ptxt = state.font.render("Press E to attune", True, (240, 240, 255))
                    screen.blit(ptxt, (int(pos.x - ptxt.get_width() / 2), int(pos.y - r - 34)))

        if getattr(state, "boss_door_closed", False):
            boss_door_world = get_field_boss_arena_door_rect(ROOM3_FIELD_WIDTH, ROOM3_FIELD_HEIGHT)
            boss_door = boss_door_world.move(int(-cam.x), int(-cam.y))
            pygame.draw.rect(screen, (90, 60, 20), boss_door)
            pygame.draw.rect(screen, (180, 140, 60), boss_door, 3)

        if state.spirit_spawned and not state.spirit_departed:
            spirit_world = get_spirit_rect_world()
            spirit_rect = spirit_world.move(int(-cam.x), int(-cam.y))
            glow = spirit_rect.inflate(24, 24)
            pygame.draw.ellipse(screen, (140, 220, 255), glow)
            pygame.draw.ellipse(screen, (40, 80, 120), glow, 3)
            pygame.draw.ellipse(screen, (220, 250, 255), spirit_rect)
            pygame.draw.ellipse(screen, (40, 80, 120), spirit_rect, 2)
            if state.font and spirit_world.inflate(160, 160).collidepoint(player.pos.x, player.pos.y):
                prompt = state.font.render("Press E to talk", True, (240, 240, 255))
                screen.blit(prompt, (spirit_rect.centerx - prompt.get_width() // 2, spirit_rect.top - 30))

        icon_x = t_rect.centerx - 16
        icon_y = t_rect.centery - 16
        if LEATHER_ARMOR_UNLOCKED and not state.leather_armor_bought:
            pygame.draw.rect(screen, (139, 69, 19), (icon_x, icon_y, 32, 32))
        label = "Leather Armor - unavailable"
        tip = "Not available yet"
        if LEATHER_ARMOR_UNLOCKED:
            label = (
                f"Leather Armor - {settings.SPEED_POTION_COST} coins"
                if not state.leather_armor_bought
                else "SOLD OUT"
            )
            tip = "Press E to buy" if not state.leather_armor_bought else "You own it!"
        label_surf = state.font.render(label, True, (255, 255, 255))
        tip_surf = state.font.render(tip, True, (220, 220, 220))
        screen.blit(label_surf, (t_rect.centerx - label_surf.get_width() // 2, t_rect.top - 28))
        screen.blit(tip_surf, (t_rect.centerx - tip_surf.get_width() // 2, t_rect.bottom + 14))

    if player.health > 0:
        p_screen = player.pos - cam
        screen_out = screen
        player_layer: pygame.Surface | None = None
        layer_offset = pygame.Vector2(0, 0)
        if player.is_dodging:
            layer_size = max(220, int(settings.PLAYER_RADIUS * 7))
            player_layer = pygame.Surface((layer_size, layer_size), pygame.SRCALPHA)
            screen = player_layer
            layer_offset = pygame.Vector2(layer_size / 2 - p_screen.x, layer_size / 2 - p_screen.y)

        p = p_screen + layer_offset
        hip_y = p.y + settings.PLAYER_RADIUS * 0.6
        leg_len = settings.PLAYER_RADIUS + 16
        leg_swing = 0
        move_speed = player.speed if player.health > 0 else 0
        keys_down = keys[pygame.K_w] or keys[pygame.K_a] or keys[pygame.K_s] or keys[pygame.K_d]
        time_tick = pygame.time.get_ticks()
        if move_speed > 0 and keys_down:
            leg_swing = int(18 * math.sin(time_tick * 0.011))
        # small idle bob for breathing / animation
        bob = math.sin(time_tick * 0.004) * 2
        leg_thickness = 12
        left_hip = (int(p.x - 18), int(hip_y))
        left_foot = (int(p.x - 20 + leg_swing), int(hip_y + leg_len))
        right_hip = (int(p.x + 18), int(hip_y))
        right_foot = (int(p.x + 20 - leg_swing), int(hip_y + leg_len))
        pygame.draw.line(screen, (60, 0, 0), left_hip, left_foot, leg_thickness)
        pygame.draw.line(screen, (60, 0, 0), right_hip, right_foot, leg_thickness)

        # Small boots at the feet (wide, short) for more character.
        boot_w, boot_h = 18, 8
        boot_col = (35, 25, 20)
        boot_outline = (10, 10, 10)
        boot_highlight = (80, 60, 45)
        for fx, fy in (left_foot, right_foot):
            boot = pygame.Rect(int(fx - boot_w / 2), int(fy - boot_h / 2), boot_w, boot_h)
            pygame.draw.rect(screen, boot_col, boot, border_radius=3)
            pygame.draw.rect(screen, boot_outline, boot, 2, border_radius=3)
            pygame.draw.line(screen, boot_highlight, (boot.left + 2, boot.top + 2), (boot.right - 2, boot.top + 2), 2)
        attack_dir = (
            get_swing_dir(player.swing_base_dir, player.swing_timer, settings.PLAYER_SWING_TIME, player.facing)
            if player.swing_timer > 0
            else (player.facing if player.facing.length_squared() > 0 else pygame.Vector2(1, 0))
        )
        base_body_color = (200, 90, 80)
        if player.is_dodging:
            base_body_color = (120, 200, 120)
        head_center = pygame.Vector2(p.x, p.y - settings.PLAYER_RADIUS * 0.85 + bob)
        head_radius = settings.PLAYER_RADIUS // 2
        body_width = int(settings.PLAYER_RADIUS * 1.4)
        body_height = int(settings.PLAYER_RADIUS * 1.8)
        body_rect = pygame.Rect(
            int(p.x - body_width // 2),
            int(p.y - body_height // 2 + bob),
            body_width,
            body_height,
        )
        leg_center = (int(p.x), int(p.y + settings.PLAYER_RADIUS * 0.6))
        leg_radius = settings.PLAYER_RADIUS // 2 + 6

        head_color = (235, 205, 160) if player.head_item else (200, 180, 160)
        body_color = (170, 100, 90) if not player.armor_equipped else (150, 120, 80)
        leg_color = (100, 60, 50)
        arm_color = (170, 110, 80)
        arm_len = int(settings.PLAYER_SWING_DISTANCE * 0.8)
        shoulder_y = body_rect.top + int(body_height * 0.2)
        arm_x_offset = body_width // 2 - 4  # keep close to torso without being flush
        arm_drop = settings.PLAYER_RADIUS * 0.05

        move_dir = pygame.Vector2(0, 0)
        if keys[pygame.K_w]:
            move_dir.y -= 1
        if keys[pygame.K_s]:
            move_dir.y += 1
        if keys[pygame.K_a]:
            move_dir.x -= 1
        if keys[pygame.K_d]:
            move_dir.x += 1

        # Idle pose: arms hang down with ~30 deg outward angle, with light swing tied to legs
        rest_angle = math.radians(30)
        sway_angle = math.radians(leg_swing * 0.3)
        arm_angle = rest_angle + sway_angle
        idle_arm_dir = pygame.Vector2(math.sin(arm_angle), math.cos(arm_angle))  # right arm points down/out
        if move_dir.length_squared() > 0:
            # bias arm slightly toward movement direction without opening the armpit too wide
            idle_arm_dir = idle_arm_dir.lerp(move_dir.normalize(), 0.25)
        if idle_arm_dir.length_squared() == 0:
            idle_arm_dir = pygame.Vector2(0.5, 1)
        idle_arm_dir = idle_arm_dir.normalize()

        swing_progress = swing_ease(player.swing_timer, settings.PLAYER_SWING_TIME) if player.swing_timer > 0 else 0.0
        swing_reach = swing_reach_multiplier(player.swing_timer, settings.PLAYER_SWING_TIME) if player.swing_timer > 0 else 1.0
        arm_dir = pygame.Vector2(idle_arm_dir)
        reach_mult = 1.0

        if player.swing_timer > 0:
            target_dir = pygame.Vector2(attack_dir)
            if target_dir.length_squared() == 0:
                target_dir = pygame.Vector2(1, 0)
            target_dir = target_dir.normalize()
            arm_dir = idle_arm_dir.lerp(target_dir, swing_progress).normalize()
            reach_mult = swing_reach
            player.last_swing_reach = reach_mult
        elif player.swing_recover_timer > 0:
            recover_blend = swing_ease(player.swing_recover_timer, settings.PLAYER_SWING_RECOVER_TIME)
            arm_dir = pygame.Vector2(player.last_attack_dir).lerp(idle_arm_dir, recover_blend)
            if arm_dir.length_squared() == 0:
                arm_dir = pygame.Vector2(idle_arm_dir)
            arm_dir = arm_dir.normalize()
            reach_mult = player.last_swing_reach + (1.0 - player.last_swing_reach) * recover_blend
        # else: arm_dir stays at idle, reach_mult at 1

        arm_drop_vec = pygame.Vector2(0, arm_drop)

        # legs
        pygame.draw.circle(screen, leg_color, leg_center, leg_radius)
        # Body with simple outline and trim
        outline_rect = body_rect.inflate(6, 6)
        pygame.draw.rect(screen, (60, 40, 40), outline_rect, border_radius=6)
        pygame.draw.rect(screen, base_body_color, body_rect, border_radius=6)
        inner_body = body_rect.inflate(-8, -8)
        pygame.draw.rect(screen, body_color, inner_body, border_radius=4)
        panel_rect = inner_body.inflate(
            -int(inner_body.width * 0.35),
            -int(inner_body.height * 0.2),
        )
        pygame.draw.rect(screen, (210, 160, 160) if not player.armor_equipped else (190, 150, 90), panel_rect, border_radius=4)
        belt_rect = pygame.Rect(inner_body.left, inner_body.centery + 6, inner_body.width, 10)
        pygame.draw.rect(screen, (60, 40, 20), belt_rect, border_radius=4)
        hem_rect = pygame.Rect(inner_body.left, inner_body.bottom - 10, inner_body.width, 8)
        pygame.draw.rect(screen, (80, 40, 40), hem_rect, border_radius=3)

        left_arm_start = pygame.Vector2(p.x - arm_x_offset, shoulder_y)
        if player.swing_timer > 0 or player.swing_recover_timer > 0:
            # Freeze shield arm during sword swings
            left_arm_end_vec = left_arm_start + pygame.Vector2(0, arm_len * 0.6)
        else:
            # left arm swings opposite to right
            left_arm_dir = pygame.Vector2(-arm_dir.x, arm_dir.y * 0.9)
            left_arm_end_vec = left_arm_start + left_arm_dir.normalize() * int(arm_len * 0.9) + arm_drop_vec
        right_arm_start = pygame.Vector2(p.x + arm_x_offset, shoulder_y)
        right_arm_end_vec = right_arm_start + arm_dir * arm_len + arm_drop_vec

        pygame.draw.line(screen, arm_color, left_arm_start, left_arm_end_vec, 8)
        pygame.draw.line(screen, arm_color, right_arm_start, right_arm_end_vec, 8)

        # Weapon held in right hand (moves with arm/facing)
        sword_dir = arm_dir
        grip_len = int(settings.SWORD_LENGTH * 0.3 * reach_mult)
        blade_len = int(settings.SWORD_LENGTH * reach_mult)
        grip_end = right_arm_end_vec + sword_dir * grip_len
        blade_tip = grip_end + sword_dir * blade_len
        cross_half = int(settings.SWORD_LENGTH * 0.18)
        perp = pygame.Vector2(-sword_dir.y, sword_dir.x)
        cross_left = grip_end + perp * cross_half
        cross_right = grip_end - perp * cross_half

        # Draw sword only if it's equipped
        if player.weapon_item == settings.ITEM_RUSTY_SWORD:
            # If bow is equipped and active, show bow animation instead
            if player.bow_equipped and player.bow_cooldown > 0:
                bow_base_left = right_arm_end_vec + perp * cross_half
                bow_base_right = right_arm_end_vec - perp * cross_half
                bow_tip = right_arm_end_vec + sword_dir * (settings.SWORD_LENGTH * 0.9)
                pygame.draw.polygon(
                    screen,
                    (200, 200, 255),
                    [
                        (int(bow_base_left.x), int(bow_base_left.y)),
                        (int(bow_base_right.x), int(bow_base_right.y)),
                        (int(bow_tip.x), int(bow_tip.y)),
                    ],
                    2,
                )
                pygame.draw.circle(screen, (80, 50, 30), right_arm_end_vec, 6)  # hand/pommel
            else:
                # Zelda-like sword visuals
                pygame.draw.line(screen, (120, 80, 40), right_arm_end_vec, grip_end, 8)  # grip
                pygame.draw.line(screen, (220, 180, 70), cross_left, cross_right, 6)  # crossguard
                pygame.draw.line(screen, (180, 210, 255), grip_end, blade_tip, 8)  # blade
                pygame.draw.circle(screen, (80, 50, 30), right_arm_end_vec, 6)  # pommel/hand
        elif player.bow_equipped:
            # Draw bow when equipped (idle or firing)
            bow_base_left = right_arm_end_vec + perp * cross_half
            bow_base_right = right_arm_end_vec - perp * cross_half
            bow_tip = right_arm_end_vec + sword_dir * (settings.SWORD_LENGTH * 0.9)
            if player.bow_cooldown > 0:
                pygame.draw.polygon(
                    screen,
                    (200, 200, 255),
                    [
                        (int(bow_base_left.x), int(bow_base_left.y)),
                        (int(bow_base_right.x), int(bow_base_right.y)),
                        (int(bow_tip.x), int(bow_tip.y)),
                    ],
                    2,
                )
            else:
                # idle bow as a filled triangle
                pygame.draw.polygon(screen, (180, 200, 230), [
                    (int(bow_base_left.x), int(bow_base_left.y)),
                    (int(bow_base_right.x), int(bow_base_right.y)),
                    (int(bow_tip.x), int(bow_tip.y)),
                ])
        if player.armor_equipped:
            # Simple chest plate overlay plus shoulder pads
            pygame.draw.rect(screen, (200, 170, 90), inner_body.inflate(-10, -10), 4, border_radius=6)
            pad_radius = 10
            pad_offset = body_width // 2 - 6
            pygame.draw.circle(screen, (180, 150, 80), (int(p.x - pad_offset), shoulder_y), pad_radius)
            pygame.draw.circle(screen, (180, 150, 80), (int(p.x + pad_offset), shoulder_y), pad_radius)
        else:
            # Cloth collar/trim when not armored
            collar = pygame.Rect(inner_body.left, inner_body.top - 6, inner_body.width, 8)
            pygame.draw.rect(screen, (220, 200, 200), collar, border_radius=4)
        if getattr(player, "shield_item", "") == settings.ITEM_RUSTY_SHIELD:
            # Zelda-like shield: equilateral top linked to a lower triangle, always visible on left arm
            body_center = pygame.Vector2(p.x, p.y)
            # Shift toward torso when blocking but stop halfway instead of centering on the body
            shift_toward_body = 0.5 if player.is_blocking else 0.25
            anchor_base = left_arm_end_vec + (body_center - left_arm_end_vec) * shift_toward_body
            # Keep the shield locked in place during sword swings so it doesn't slide when attacking
            if player.swing_timer > 0 or player.swing_recover_timer > 0:
                shield_anchor = body_center + player.shield_anchor_offset
            else:
                shield_anchor = anchor_base
                player.shield_anchor_offset = shield_anchor - body_center

            base_half = 28  # smaller shield
            top_height = base_half * math.sqrt(3)  # equilateral triangle height for side = base_half*2
            bottom_height = 72  # slightly shorter lower point

            base_offset_y = 6
            base_left = shield_anchor + pygame.Vector2(-base_half, base_offset_y)
            base_right = shield_anchor + pygame.Vector2(base_half, base_offset_y)

            # Equilateral top triangle (pointing upward/left-ish), shares base with bottom
            top_tip = shield_anchor + pygame.Vector2(-base_half * 0.1, base_offset_y - top_height)

            # Bottom triangle (pointing downward, slightly inset toward center)
            bottom_tip = shield_anchor + pygame.Vector2(-base_half * 0.12, base_offset_y + bottom_height)

            main_color = (96, 140, 200)
            accent_color = (150, 200, 255)
            outline_color = (60, 100, 160)

            pygame.draw.polygon(screen, main_color, [top_tip, base_left, base_right])
            pygame.draw.polygon(screen, accent_color, [base_left, base_right, bottom_tip])
            pygame.draw.lines(
                screen,
                outline_color,
                False,
                [top_tip, base_left, bottom_tip, base_right, top_tip],
                4,
            )
            pygame.draw.line(screen, outline_color, base_left, base_right, 3)

        # Draw head last so arms/weapons don't cut across it.
        pygame.draw.circle(screen, head_color, head_center, head_radius)
        # Eyes: only look left/right when facing that way.
        look_x = float(player.facing.x)
        if abs(look_x) < 0.35:
            pupil_dir = pygame.Vector2(0, 0)
        else:
            pupil_dir = pygame.Vector2(1 if look_x > 0 else -1, 0)
        eye_sep = head_radius * 0.45
        eye_drop = head_radius * 0.12
        eye_r = max(3, int(head_radius * 0.20))
        pupil_r = max(2, int(eye_r * 0.65))
        pupil_max = max(0.0, eye_r - pupil_r - 1.0)
        pupil_off = pupil_dir * pupil_max
        for side in (-1, 1):
            eye_center = head_center + pygame.Vector2(side * eye_sep, eye_drop)
            pygame.draw.circle(screen, (250, 250, 250), (int(eye_center.x), int(eye_center.y)), eye_r)
            pupil_center = eye_center + pupil_off
            pygame.draw.circle(screen, (20, 20, 20), (int(pupil_center.x), int(pupil_center.y)), pupil_r)

        if player_layer is not None:
            dur = max(0.001, settings.DODGE_DURATION)
            phase = 1.0 - max(0.0, min(1.0, player.dodge_timer / dur))
            roll_dir = pygame.Vector2(getattr(player, "dodge_dir", pygame.Vector2(0, 0)))
            if roll_dir.length_squared() == 0:
                roll_dir = pygame.Vector2(getattr(player, "facing", pygame.Vector2(0, -1)))
            if roll_dir.length_squared() == 0:
                roll_dir = pygame.Vector2(0, -1)
            roll_dir = roll_dir.normalize()

            # Rotate the sprite so the head leads the roll direction (head-first).
            face_deg = math.degrees(math.atan2(roll_dir.x, -roll_dir.y))  # 0=up, 90=right, 180=down, -90=left

            # Spin direction: pick a consistent "forward tumble" feel.
            if abs(roll_dir.x) >= abs(roll_dir.y):
                spin_sign = 1.0 if roll_dir.x < 0 else -1.0
            else:
                spin_sign = -1.0 if roll_dir.y > 0 else 1.0

            tumble_deg = phase * 360.0 * spin_sign
            angle = (-face_deg) + tumble_deg
            rotated = pygame.transform.rotozoom(player_layer, angle, 1.0)
            rect = rotated.get_rect(center=(int(p_screen.x), int(p_screen.y)))
            screen_out.blit(rotated, rect)
            screen = screen_out

    for coin in state.coin_pickups:
        cpos = coin["pos"] - cam
        pygame.draw.circle(screen, (255, 215, 0), (int(cpos.x), int(cpos.y)), 10)
        pygame.draw.circle(screen, (90, 70, 0), (int(cpos.x), int(cpos.y)), 10, 2)

    if state.door_revealed:
        door = get_door_rect_world(state).move(int(-cam.x), int(-cam.y))
        if state.level_index == 1:
            pygame.draw.rect(screen, settings.FIRST_ROOM_DOOR_COLOR, door)
            pygame.draw.rect(screen, settings.FIRST_ROOM_DOOR_OUTLINE, door, 6)
        else:
            pygame.draw.rect(screen, (90, 60, 20), door)
            pygame.draw.rect(screen, (180, 140, 60), door, 3)

    for pig in state.pigs:
        if pig.health <= 0:
            continue
        # Pig appearance: upright pink pig with head, snout, ears, arms, legs and a sword
        pp = pig.pos - cam
        # Leg swing driven by distance walked; freeze while attacking
        moving = pig.windup_timer <= 0 and pig.swing_timer <= 0
        pig_leg_swing = int(12 * math.sin(pig.walk_cycle)) if moving else 0

        # Body dimensions
        body_w = int(pig.radius * 1.8)
        body_h = int(pig.radius * 1.2)
        body_rect = pygame.Rect(int(pp.x - body_w / 2), int(pp.y - body_h / 2), body_w, body_h)

        if getattr(pig, "is_ally", False):
            PINK = (140, 220, 255)
            DARK_PINK = (60, 140, 200)
            SNOUT = (180, 245, 255)
        else:
            PINK = (255, 160, 180)
            DARK_PINK = (200, 120, 140)
            SNOUT = (255, 140, 160)

        # Draw body (oval)
        pygame.draw.ellipse(screen, PINK, body_rect)
        pygame.draw.ellipse(screen, DARK_PINK, body_rect, 2)

        # Head above body
        head_offset = pygame.Vector2(0, -body_h * 0.6)
        head_center = pp + head_offset
        head_radius = int(body_h * 0.5)
        pygame.draw.circle(screen, PINK, (int(head_center.x), int(head_center.y)), head_radius)
        pygame.draw.circle(screen, DARK_PINK, (int(head_center.x), int(head_center.y)), head_radius, 2)

        # Snout (in front of head based on facing)
        facing = pig.facing if pig.facing.length_squared() > 0 else pygame.Vector2(1, 0)
        snout_dir = facing.normalize()
        snout_center = head_center + snout_dir * (head_radius * 0.5)
        pygame.draw.circle(screen, SNOUT, (int(snout_center.x), int(snout_center.y)), int(head_radius * 0.4))
        pygame.draw.circle(screen, (100, 40, 40), (int(snout_center.x), int(snout_center.y)), int(head_radius * 0.12))

        # Ears (two small triangles)
        ear_offset = pygame.Vector2(head_radius * 0.6, -head_radius * 0.6)
        left_ear = [
            (int(head_center.x - ear_offset.x), int(head_center.y + ear_offset.y)),
            (int(head_center.x - ear_offset.x - 6), int(head_center.y + ear_offset.y - 12)),
            (int(head_center.x - ear_offset.x + 6), int(head_center.y + ear_offset.y - 12)),
        ]
        right_ear = [
            (int(head_center.x + ear_offset.x), int(head_center.y + ear_offset.y)),
            (int(head_center.x + ear_offset.x - 6), int(head_center.y + ear_offset.y - 12)),
            (int(head_center.x + ear_offset.x + 6), int(head_center.y + ear_offset.y - 12)),
        ]
        pygame.draw.polygon(screen, PINK, left_ear)
        pygame.draw.polygon(screen, PINK, right_ear)
        pygame.draw.polygon(screen, DARK_PINK, left_ear, 1)
        pygame.draw.polygon(screen, DARK_PINK, right_ear, 1)

        # Eyes
        eye_offset = pygame.Vector2(head_radius * 0.3, -head_radius * 0.1)
        left_eye = head_center + pygame.Vector2(-eye_offset.x, eye_offset.y)
        right_eye = head_center + pygame.Vector2(eye_offset.x, eye_offset.y)
        pygame.draw.circle(screen, (30, 30, 30), (int(left_eye.x), int(left_eye.y)), 3)
        pygame.draw.circle(screen, (30, 30, 30), (int(right_eye.x), int(right_eye.y)), 3)

        # Tail (curly)
        tail_base = pp + pygame.Vector2(body_w / 2, -body_h * 0.2)
        pygame.draw.arc(screen, DARK_PINK, (int(tail_base.x), int(tail_base.y), 14, 14), 3.14, 5.0, 3)

        # Lock-on indicator
        if state.lock_target is pig:
            icon_center = head_center + pygame.Vector2(0, -head_radius * 1.2)
            pygame.draw.circle(screen, (255, 240, 150), (int(icon_center.x), int(icon_center.y)), 8, 2)
            pygame.draw.polygon(
                screen,
                (255, 240, 150),
                [
                    (int(icon_center.x), int(icon_center.y) + 10),
                    (int(icon_center.x) - 6, int(icon_center.y) + 2),
                    (int(icon_center.x) + 6, int(icon_center.y) + 2),
                ],
                0,
            )

        # Legs
        leg_y = int(pp.y + body_h * 0.35)
        left_leg_start = (int(pp.x - body_w * 0.28), leg_y - 6)
        left_leg_end = (int(pp.x - body_w * 0.28 + pig_leg_swing), int(leg_y + pig.radius * 0.5))
        right_leg_start = (int(pp.x + body_w * 0.28), leg_y - 6)
        right_leg_end = (int(pp.x + body_w * 0.28 - pig_leg_swing), int(leg_y + pig.radius * 0.5))
        pygame.draw.line(screen, DARK_PINK, left_leg_start, left_leg_end, 8)
        pygame.draw.line(screen, DARK_PINK, right_leg_start, right_leg_end, 8)

        # Arms and sword
        pig_draw_dir = (
            get_swing_dir(pig.swing_base_dir, pig.swing_timer, pig.swing_time, pig.facing)
            if pig.swing_timer > 0
            else pig.facing
        )
        pig_swing_reach = swing_reach_multiplier(pig.swing_timer, pig.swing_time) if pig.swing_timer > 0 else 1.0
        # Arm origin slightly above body center
        arm_origin = pp + pygame.Vector2(0, -body_h * 0.1)
        arm_len = int(settings.SWORD_LENGTH * 0.5 * pig_swing_reach)
        grip_end = arm_origin + pig_draw_dir.normalize() * arm_len
        # Draw arm
        pygame.draw.line(screen, DARK_PINK, (int(arm_origin.x), int(arm_origin.y)), (int(grip_end.x), int(grip_end.y)), 6)

        # Draw sword swing polygon or idle sword
        es_pts = sword_polygon_points(
            arm_origin,
            pig_draw_dir,
            settings.PIG_SWING_DISTANCE * pig_swing_reach,
            settings.SWORD_LENGTH * pig_swing_reach,
            settings.SWORD_WIDTH,
        )
        if pig.swing_timer > 0:
            pygame.draw.polygon(screen, (220, 200, 180), es_pts)
        else:
            # idle sword: simple line + pommel
            tip = grip_end + pig_draw_dir.normalize() * settings.SWORD_LENGTH
            pygame.draw.line(screen, (120, 80, 40), (int(grip_end.x), int(grip_end.y)), (int(tip.x), int(tip.y)), 6)
            perp = pygame.Vector2(-pig_draw_dir.y, pig_draw_dir.x).normalize()
            cross_left = grip_end + perp * int(settings.SWORD_LENGTH * 0.18)
            cross_right = grip_end - perp * int(settings.SWORD_LENGTH * 0.18)
            pygame.draw.line(screen, (220, 180, 70), (int(cross_left.x), int(cross_left.y)), (int(cross_right.x), int(cross_right.y)), 4)
            pygame.draw.circle(screen, (80, 50, 30), (int(arm_origin.x), int(arm_origin.y)), 5)

        if not pig.is_boss and not getattr(pig, "is_ally", False):
            draw_health_bar_above(screen, pp, pig.health, pig.max_health, radius=pig.radius)

    # Draw arrows
    arrow_color = (240, 230, 200)
    for arrow in state.arrows:
        pos = arrow["pos"]
        dir_vec = arrow["dir"]
        tail = pos - dir_vec * 10
        head = pos + dir_vec * 16
        pygame.draw.line(screen, arrow_color, tail, head, 6)
        perp = pygame.Vector2(-dir_vec.y, dir_vec.x) * 4
        pygame.draw.polygon(
            screen,
            (200, 200, 255),
            [
                (head.x, head.y),
                (head.x - dir_vec.x * 10 + perp.x, head.y - dir_vec.y * 10 + perp.y),
                (head.x - dir_vec.x * 10 - perp.x, head.y - dir_vec.y * 10 - perp.y),
            ],
        )

    # Player sword swing visuals are handled by the arm/sword drawing above; no extra hitbox polygon needed.

    if state.blood_splats:
        blood_color = (160, 0, 0)
        for s in state.blood_splats:
            for pos, rad in s["points"]:
                pygame.draw.circle(screen, blood_color, (int(pos.x), int(pos.y)), int(rad), 1)

    boss = next((p for p in state.pigs if getattr(p, "is_boss", False) and p.health > 0), None)
    if boss is not None and state.font is not None:
        # Draw boss bar on the real screen later (not zoomed).
        pass

    # Scale world -> screen
    scaled = pygame.transform.smoothscale(screen, real_screen.get_size())
    real_screen.blit(scaled, (0, 0))

    # UI (not zoomed)
    screen = real_screen
    health_w = draw_player_health_bar_topleft(screen, player.health, player.max_health, 10, 10)
    stamina_w = draw_player_stamina_bar_topleft(
        screen,
        player.stamina,
        settings.STAMINA_MAX,
        10,
        26,
        exhausted=getattr(player, "stamina_exhausted", False),
    )
    hud_right = 10 + max(health_w, stamina_w)
    draw_potion_icon(screen, hud_right + 10, 6, enabled="heal" if player.potion_count > 0 else None)
    draw_coin_icon(screen, hud_right + 34, 6, enabled=True)
    coins_text = state.font.render(f"x {state.coin_count}", True, (255, 255, 255))
    screen.blit(coins_text, (hud_right + 66, 6))

    if boss is not None and state.font is not None:
        draw_boss_health_bar_bottom(screen, state.font, "Pig Boss", boss.health, boss.max_health)

    if getattr(state, "toast_text", "") and state.font:
        msg = state.font.render(state.toast_text, True, (255, 255, 255))
        back = msg.get_rect()
        back.inflate_ip(24, 16)
        back.center = (screen.get_width() // 2, 70)
        pygame.draw.rect(screen, (20, 20, 40), back, border_radius=10)
        pygame.draw.rect(screen, (160, 160, 210), back, 2, border_radius=10)
        screen.blit(msg, (back.centerx - msg.get_width() // 2, back.centery - msg.get_height() // 2))

    if getattr(state, "fast_travel_active", False):
        t = float(getattr(state, "fast_travel_timer", 0.0))
        dur = max(0.001, float(getattr(state, "fast_travel_duration", 1.2)))
        u = max(0.0, min(1.0, t / dur))
        fade = u * 2 if u < 0.5 else (1 - (u - 0.5) * 2)
        alpha = int(255 * fade)
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        screen.blit(overlay, (0, 0))

    if state.inventory_open:
        draw_inventory_panel(state)

    if state.dialogue_lines:
        draw_dialogue(state)

    if state.map_open and state.has_map:
        # map handled above
        return
    return


def run():
    pygame.init()
    screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
    state = create_game_state(screen)
    if not state.intro_active:
        reset_round(state)
        start_mode = getattr(state, "debug_start", None)
        if start_mode == "post_bow":
            apply_post_bow_start(state, coin_count=10)
        elif start_mode == "post_boss":
            apply_post_boss_start(state, coin_count=75)

    while state.running:
        events = pygame.event.get()
        if state.intro_active:
            update_intro(state, events)
            if state.intro_active:
                draw_intro(state)
                pygame.display.flip()
                state.dt = state.clock.tick(settings.TARGET_FPS) / 1000
                continue
            # Intro ended this frame; start fresh next loop without reusing events
            state.dt = state.clock.tick(settings.TARGET_FPS) / 1000
            continue

        if state.game_over:
            handle_death_screen(state, events)
            continue

        handle_events(state, events)
        update_game(state)
        draw_game(state)
        pygame.display.flip()
        state.dt = state.clock.tick(settings.TARGET_FPS) / 1000

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run()
