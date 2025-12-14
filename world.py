from __future__ import annotations

import random
from typing import Tuple

import pygame

import settings


_FIELD_ENV_CACHE: dict[tuple[int, int], pygame.Surface] = {}
_FIELD_MAP_CACHE: dict[tuple[int, int, int, int], pygame.Surface] = {}

ENV_MARGIN = 24


def _clamp_rect_in_bounds(rect: pygame.Rect, width: int, height: int, margin: int = ENV_MARGIN) -> pygame.Rect:
    rect = rect.copy()
    rect.x = max(margin, min(rect.x, width - rect.width - margin))
    rect.y = max(margin, min(rect.y, height - rect.height - margin))
    return rect


def _draw_road(surface: pygame.Surface, rect: pygame.Rect):
    road_fill = (196, 170, 110)
    road_edge = (130, 110, 70)
    pygame.draw.rect(surface, road_fill, rect)
    pygame.draw.rect(surface, road_edge, rect, 6)
    # light center stripe
    inner = rect.inflate(-24, -24)
    if inner.width > 0 and inner.height > 0:
        pygame.draw.rect(surface, (210, 190, 135), inner, 2)


def _draw_house(surface: pygame.Surface, rect: pygame.Rect, roof_color=(150, 70, 70)):
    wall = (200, 190, 150)
    outline = (70, 60, 40)
    pygame.draw.rect(surface, wall, rect, border_radius=8)
    pygame.draw.rect(surface, outline, rect, 4, border_radius=8)

    roof_h = int(rect.height * 0.55)
    roof = [
        (rect.left - 10, rect.top + 8),
        (rect.centerx, rect.top - roof_h),
        (rect.right + 10, rect.top + 8),
    ]
    pygame.draw.polygon(surface, roof_color, roof)
    pygame.draw.polygon(surface, outline, roof, 4)

    door = pygame.Rect(0, 0, int(rect.width * 0.18), int(rect.height * 0.42))
    door.midbottom = (rect.centerx, rect.bottom - 6)
    pygame.draw.rect(surface, (120, 80, 40), door, border_radius=4)
    pygame.draw.rect(surface, outline, door, 3, border_radius=4)
    pygame.draw.circle(surface, (230, 210, 120), (door.right - 8, door.centery), 4)

    win_w = int(rect.width * 0.18)
    win_h = int(rect.height * 0.18)
    for sx in (-1, 1):
        win = pygame.Rect(0, 0, win_w, win_h)
        win.center = (rect.centerx + sx * int(rect.width * 0.22), rect.centery - int(rect.height * 0.10))
        pygame.draw.rect(surface, (120, 170, 210), win, border_radius=3)
        pygame.draw.rect(surface, outline, win, 2, border_radius=3)
        pygame.draw.line(surface, outline, (win.centerx, win.top + 2), (win.centerx, win.bottom - 2), 2)
        pygame.draw.line(surface, outline, (win.left + 2, win.centery), (win.right - 2, win.centery), 2)


def _draw_farm(surface: pygame.Surface, rect: pygame.Rect):
    soil = (70, 120, 60)
    fence = (120, 90, 50)
    outline = (60, 40, 20)
    pygame.draw.rect(surface, soil, rect, border_radius=6)
    pygame.draw.rect(surface, fence, rect, 4, border_radius=6)
    pygame.draw.rect(surface, outline, rect, 2, border_radius=6)
    # crop rows
    row_color = (90, 150, 70)
    for x in range(rect.left + 14, rect.right - 14, 18):
        pygame.draw.line(surface, row_color, (x, rect.top + 10), (x, rect.bottom - 10), 2)


def _draw_tree(surface: pygame.Surface, center: pygame.Vector2, size: int):
    trunk = pygame.Rect(int(center.x - size * 0.12), int(center.y + size * 0.10), int(size * 0.24), int(size * 0.40))
    pygame.draw.rect(surface, (90, 60, 30), trunk, border_radius=4)
    pygame.draw.circle(surface, (30, 120, 50), (int(center.x), int(center.y)), int(size * 0.55))
    pygame.draw.circle(surface, (50, 160, 70), (int(center.x - size * 0.15), int(center.y - size * 0.15)), int(size * 0.22))
    pygame.draw.circle(surface, (20, 90, 40), (int(center.x + size * 0.18), int(center.y + size * 0.08)), int(size * 0.26), 2)


def get_field_house_rects(field_width: int, field_height: int) -> list[pygame.Rect]:
    """House footprint rects in field world coordinates (solid)."""
    shop_x = int(settings.SCREEN_WIDTH * 0.12)
    shop_y = int(settings.SCREEN_HEIGHT * 0.60)

    houses = [
        pygame.Rect(shop_x + 260, shop_y - 320, 120, 110),
        pygame.Rect(shop_x + 560, shop_y - 220, 130, 120),
        pygame.Rect(shop_x + 300, shop_y - 120, 120, 110),
    ]
    return [_clamp_rect_in_bounds(r, field_width, field_height) for r in houses]


def get_field_house_solid_rects(field_width: int, field_height: int) -> list[pygame.Rect]:
    """Solid collision rects for houses, including roof overhang."""
    solids: list[pygame.Rect] = []
    for house in get_field_house_rects(field_width, field_height):
        roof_h = int(house.height * 0.55)
        roof_bounds = pygame.Rect(house.left - 12, house.top - roof_h - 6, house.width + 24, roof_h + 18)
        solid = house.union(roof_bounds)
        solids.append(_clamp_rect_in_bounds(solid, field_width, field_height))
    return solids


def get_field_boss_arena_rect(field_width: int, field_height: int) -> pygame.Rect:
    center = (int(field_width * 0.85), int(field_height * 0.25))
    arena = pygame.Rect(0, 0, 980, 720)
    arena.center = center
    return _clamp_rect_in_bounds(arena, field_width, field_height, margin=ENV_MARGIN)


def get_field_boss_arena_wall_rects(field_width: int, field_height: int) -> list[pygame.Rect]:
    arena = get_field_boss_arena_rect(field_width, field_height)
    thickness = 36
    door_w = 220
    door_w = min(door_w, arena.width - thickness * 2 - 80)
    half_gap = door_w // 2

    top = pygame.Rect(arena.left, arena.top, arena.width, thickness)
    left = pygame.Rect(arena.left, arena.top, thickness, arena.height)
    right = pygame.Rect(arena.right - thickness, arena.top, thickness, arena.height)

    bottom_y = arena.bottom - thickness
    gap_left = arena.centerx - half_gap
    gap_right = arena.centerx + half_gap
    bottom_left = pygame.Rect(arena.left, bottom_y, max(0, gap_left - arena.left), thickness)
    bottom_right = pygame.Rect(gap_right, bottom_y, max(0, arena.right - gap_right), thickness)
    walls = [top, left, right]
    if bottom_left.width > 0:
        walls.append(bottom_left)
    if bottom_right.width > 0:
        walls.append(bottom_right)
    return walls


def get_field_boss_arena_door_rect(field_width: int, field_height: int) -> pygame.Rect:
    arena = get_field_boss_arena_rect(field_width, field_height)
    thickness = 36
    door_w = 220
    door_w = min(door_w, arena.width - thickness * 2 - 80)
    door = pygame.Rect(0, 0, door_w, thickness)
    door.midtop = (arena.centerx, arena.bottom - thickness)
    return door


def build_field_environment_surface(field_width: int, field_height: int) -> pygame.Surface:
    """Build a Zelda-ish overworld environment surface (world space) for the field level."""
    surface = pygame.Surface((field_width, field_height))

    grass_base = (58, 145, 62)
    grass_light = (76, 175, 80)
    surface.fill(grass_base)

    # Subtle horizontal stripes to mimic tile variation
    stripe_h = 10
    step = 40
    for yy in range(0, field_height, step):
        pygame.draw.rect(surface, grass_light, pygame.Rect(0, yy, field_width, stripe_h))

    # Main roads
    road_w = 120
    main_h = pygame.Rect(0, int(field_height * 0.58 - road_w / 2), field_width, road_w)
    main_v = pygame.Rect(int(field_width * 0.34 - road_w / 2), 0, road_w, field_height)
    _draw_road(surface, main_h)
    _draw_road(surface, main_v)

    # Shopkeeper/table area (matches game.get_room3_table_rect positioning)
    shop_x = int(settings.SCREEN_WIDTH * 0.12)
    shop_y = int(settings.SCREEN_HEIGHT * 0.60)
    house_rects = get_field_house_rects(field_width, field_height)

    plaza = _clamp_rect_in_bounds(pygame.Rect(shop_x - 260, shop_y - 260, 620, 460), field_width, field_height)
    for r in house_rects:
        plaza = plaza.union(r.inflate(160, 160))
    plaza = _clamp_rect_in_bounds(plaza, field_width, field_height)
    pygame.draw.rect(surface, (130, 130, 140), plaza, border_radius=12)
    pygame.draw.rect(surface, (80, 80, 90), plaza, 6, border_radius=12)
    # Path that connects the shop plaza to the main road
    lane = _clamp_rect_in_bounds(
        pygame.Rect(shop_x - road_w // 2, shop_y, road_w, main_h.centery - shop_y + road_w // 2),
        field_width,
        field_height,
        margin=0,
    )
    _draw_road(surface, lane)
    lane_join = _clamp_rect_in_bounds(pygame.Rect(0, main_h.top, int(field_width * 0.22), main_h.height), field_width, field_height, margin=0)
    _draw_road(surface, lane_join)

    # Village cluster near the shop plaza
    for i, r in enumerate(house_rects):
        roof = (160, 80, 80) if i % 2 == 0 else (140, 90, 60)
        _draw_house(surface, r, roof_color=roof)

    # Boss arena near the quest point (0.85, 0.25) - large enclosed yard with a door opening.
    arena = get_field_boss_arena_rect(field_width, field_height)
    yard = arena.inflate(-72, -72)
    pygame.draw.rect(surface, (70, 90, 75), yard, border_radius=18)
    pygame.draw.rect(surface, (55, 70, 60), yard, 3, border_radius=18)
    wall_fill = (130, 130, 140)
    wall_edge = (80, 80, 90)
    for wall in get_field_boss_arena_wall_rects(field_width, field_height):
        pygame.draw.rect(surface, wall_fill, wall)
        pygame.draw.rect(surface, wall_edge, wall, 4)
    # Door frame at the opening
    door = get_field_boss_arena_door_rect(field_width, field_height)
    pygame.draw.rect(surface, wall_edge, door.inflate(12, 8), 3)

    # Farm fields to the south-east
    farms = [
        pygame.Rect(int(field_width * 0.52), int(field_height * 0.72), 360, 240),
        pygame.Rect(int(field_width * 0.72), int(field_height * 0.68), 380, 260),
    ]
    for r in farms:
        _draw_farm(surface, r)

    # Small pond to break up the grass
    pond_rect = pygame.Rect(int(field_width * 0.62), int(field_height * 0.32), 420, 260)
    pygame.draw.ellipse(surface, (40, 110, 170), pond_rect)
    pygame.draw.ellipse(surface, (170, 220, 255), pond_rect.inflate(-18, -18), 4)
    pygame.draw.ellipse(surface, (20, 70, 120), pond_rect, 4)

    # Decorative trees and shrubs (deterministic)
    rng = random.Random(1337)
    density = (field_width * field_height) / (3200 * 2400)
    tree_count = max(160, int(160 * density))
    for _ in range(tree_count):
        x = rng.randrange(0, field_width)
        y = rng.randrange(0, field_height)
        # Keep trees away from road corridors
        if abs(y - main_h.centery) < 120 or abs(x - main_v.centerx) < 120:
            continue
        # Avoid pond and key areas
        if pond_rect.collidepoint(x, y):
            continue
        if arena.inflate(120, 120).collidepoint(x, y):
            continue
        if plaza.collidepoint(x, y) or lane.collidepoint(x, y) or lane_join.collidepoint(x, y):
            continue
        size = rng.randrange(26, 52)
        _draw_tree(surface, pygame.Vector2(x, y), size)

    # A few rock clusters
    rock_color = (120, 120, 120)
    rock_shadow = (80, 80, 80)
    rocks = [
        (field_width * 0.18, field_height * 0.25),
        (field_width * 0.86, field_height * 0.86),
        (field_width * 0.44, field_height * 0.18),
        (field_width * 0.78, field_height * 0.46),
        (field_width * 0.58, field_height * 0.86),
    ]
    for rx, ry in rocks:
        pygame.draw.circle(surface, rock_shadow, (int(rx + 10), int(ry + 10)), 26)
        pygame.draw.circle(surface, rock_color, (int(rx), int(ry)), 26)
        pygame.draw.circle(surface, (180, 180, 180), (int(rx - 8), int(ry - 10)), 10)

    return surface


def get_field_environment_surface(field_width: int, field_height: int) -> pygame.Surface:
    key = (field_width, field_height)
    env = _FIELD_ENV_CACHE.get(key)
    if env is None:
        env = build_field_environment_surface(field_width, field_height)
        _FIELD_ENV_CACHE[key] = env
        _FIELD_MAP_CACHE.clear()
    return env


def get_field_map_surface(target_size: tuple[int, int], field_width: int, field_height: int) -> pygame.Surface:
    """Scaled 'image' of the environment for the map overlay."""
    key = (target_size[0], target_size[1], field_width, field_height)
    cached = _FIELD_MAP_CACHE.get(key)
    if cached is not None:
        return cached
    env = get_field_environment_surface(field_width, field_height)
    scaled = pygame.transform.smoothscale(env, target_size)
    _FIELD_MAP_CACHE[key] = scaled
    return scaled


def blit_field_environment(screen: pygame.Surface, cam: pygame.Vector2, field_width: int, field_height: int):
    env = get_field_environment_surface(field_width, field_height)
    screen.blit(env, (-int(cam.x), -int(cam.y)))


def draw_background(screen: pygame.Surface, cam_offset: pygame.Vector2, level_index: int, field_width=4500, field_height=3200):
    """Legacy helper; prefer blit_field_environment for the field."""
    if level_index == settings.FIELD_LEVEL_INDEX:
        blit_field_environment(screen, cam_offset, field_width, field_height)
    else:
        screen.fill("purple")


def get_door_rect(level_index: int, screen: pygame.Surface) -> pygame.Rect:
    if level_index == 1:
        x = screen.get_width() - settings.DOOR_MARGIN - settings.FIRST_ROOM_DOOR_WIDTH
        y = (screen.get_height() - settings.FIRST_ROOM_DOOR_HEIGHT) // 2
        return pygame.Rect(x, y, settings.FIRST_ROOM_DOOR_WIDTH, settings.FIRST_ROOM_DOOR_HEIGHT)
    x = screen.get_width() - settings.DOOR_MARGIN - settings.DOOR_WIDTH
    y = (screen.get_height() - settings.DOOR_HEIGHT) // 2
    return pygame.Rect(x, y, settings.DOOR_WIDTH, settings.DOOR_HEIGHT)


def get_room3_table_rect(screen: pygame.Surface, cam_offset: pygame.Vector2 = pygame.Vector2(0, 0)) -> pygame.Rect:
    """Table rect in room 3 (world space), optionally offset for camera."""
    table_w, table_h = 160, 60
    # Match the drawn table location in game.draw_game (left side of the field).
    t_center = pygame.Vector2(screen.get_width() * 0.12, screen.get_height() * 0.60)
    return pygame.Rect(
        int(t_center.x - table_w / 2 + cam_offset.x),
        int(t_center.y - table_h / 2 + cam_offset.y),
        table_w,
        table_h,
    )


def get_shopkeeper_rect(screen: pygame.Surface) -> pygame.Rect:
    """Rectangle for the shopkeeper standing behind the table."""
    t_rect = get_room3_table_rect(screen, pygame.Vector2(0, 0))
    return pygame.Rect(
        t_rect.centerx - settings.NPC_WIDTH // 2,
        t_rect.top - settings.NPC_HEIGHT - 6,
        settings.NPC_WIDTH,
        settings.NPC_HEIGHT,
    )
