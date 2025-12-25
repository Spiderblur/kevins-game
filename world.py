from __future__ import annotations

from collections import OrderedDict
import math
import random
from typing import Tuple

import pygame

import settings


_FIELD_MAP_CACHE: dict[tuple[int, int, int, int], pygame.Surface] = {}
_FIELD_FEATURE_CACHE: dict[tuple[int, int], dict] = {}
_FIELD_TILE_CACHE: "OrderedDict[tuple[int, int, int, int, int], pygame.Surface]" = OrderedDict()

FIELD_TILE_SIZE = 640
FIELD_TILE_CACHE_MAX = 64

ENV_MARGIN = 24


def _get_shop_village_anchor(field_width: int, field_height: int) -> pygame.Vector2:
    # Place the shop/village away from the extreme top-left so the overworld feels more expansive.
    return pygame.Vector2(int(field_width * 0.18), int(field_height * 0.14))


def _biome_seed(field_width: int, field_height: int) -> int:
    # Stable per-world seed for biome shapes/colors.
    return (field_width * 53) ^ (field_height * 97) ^ 424242


def _get_field_biomes(field_width: int, field_height: int) -> dict:
    rng = random.Random(_biome_seed(field_width, field_height))

    volcano_w = int(field_width * 0.40)
    volcano_h = int(field_height * 0.42)
    snow_w = int(field_width * 0.33)
    snow_h = int(field_height * 0.30)

    # Center clearing (an ellipse) to keep a wide open middle without biomes.
    clear_cx = field_width * 0.52
    clear_cy = field_height * 0.50
    clear_rx = field_width * 0.18
    clear_ry = field_height * 0.14

    volcano = {
        "w": volcano_w,
        "h": volcano_h,
        "amp": field_height * 0.030,
        "ph1": rng.random() * math.tau,
        "ph2": rng.random() * math.tau,
    }
    snow = {
        "w": snow_w,
        "h": snow_h,
        "amp": field_width * 0.028,
        "ph1": rng.random() * math.tau,
        "ph2": rng.random() * math.tau,
    }

    # Bounding boxes (expanded a bit for boundary wiggle) for cheap tile overlap tests.
    volcano_bbox = pygame.Rect(
        0,
        int(field_height - volcano_h - volcano["amp"] * 2 - 200),
        int(volcano_w + volcano["amp"] * 2 + 200),
        int(volcano_h + volcano["amp"] * 2 + 400),
    )
    snow_bbox = pygame.Rect(
        int(field_width - snow_w - snow["amp"] * 2 - 400),
        0,
        int(snow_w + snow["amp"] * 2 + 400),
        int(snow_h + snow["amp"] * 2 + 200),
    )
    clear_bbox = pygame.Rect(
        int(clear_cx - clear_rx - 60),
        int(clear_cy - clear_ry - 60),
        int(clear_rx * 2 + 120),
        int(clear_ry * 2 + 120),
    )

    return {
        "volcano": volcano,
        "snow": snow,
        "clear": {"cx": clear_cx, "cy": clear_cy, "rx": clear_rx, "ry": clear_ry},
        "volcano_bbox": volcano_bbox,
        "snow_bbox": snow_bbox,
        "clear_bbox": clear_bbox,
    }


def _in_center_clear(x: float, y: float, biomes: dict) -> bool:
    c = biomes["clear"]
    rx = max(1.0, float(c["rx"]))
    ry = max(1.0, float(c["ry"]))
    dx = (x - float(c["cx"])) / rx
    dy = (y - float(c["cy"])) / ry
    return (dx * dx + dy * dy) <= 1.0


def _volcano_boundary_y(x: float, field_width: int, field_height: int, biomes: dict) -> float:
    v = biomes["volcano"]
    vw = max(1.0, float(v["w"]))
    vh = float(v["h"])
    t = max(0.0, min(1.0, x / vw))
    base = (field_height - vh) + t * vh
    amp = float(v["amp"])
    ph1 = float(v["ph1"])
    ph2 = float(v["ph2"])
    jitter = (math.sin(t * 9.0 + ph1) + 0.55 * math.sin(t * 19.0 + ph2)) * amp
    return base + jitter


def _snow_boundary_x(y: float, field_width: int, field_height: int, biomes: dict) -> float:
    s = biomes["snow"]
    sw = float(s["w"])
    sh = max(1.0, float(s["h"]))
    t = max(0.0, min(1.0, y / sh))
    base = (field_width - sw) + t * sw
    amp = float(s["amp"])
    ph1 = float(s["ph1"])
    ph2 = float(s["ph2"])
    jitter = (math.sin(t * 8.0 + ph1) + 0.5 * math.sin(t * 17.0 + ph2)) * amp
    return base + jitter


def _is_in_volcano(x: float, y: float, field_width: int, field_height: int, biomes: dict) -> bool:
    if _in_center_clear(x, y, biomes):
        return False
    v = biomes["volcano"]
    if x < 0 or x > v["w"]:
        return False
    return y >= _volcano_boundary_y(x, field_width, field_height, biomes)


def _is_in_snow(x: float, y: float, field_width: int, field_height: int, biomes: dict) -> bool:
    if _in_center_clear(x, y, biomes):
        return False
    s = biomes["snow"]
    if y < 0 or y > s["h"]:
        return False
    return x >= _snow_boundary_x(y, field_width, field_height, biomes)


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


def _draw_river_tile(tile: pygame.Surface, points_world: list[pygame.Vector2], width: int, tile_world: pygame.Rect):
    local_pts = []
    for p in points_world:
        local_pts.append((int(p.x - tile_world.left), int(p.y - tile_world.top)))
    if len(local_pts) < 2:
        return

    bank_outer = (25, 80, 40)
    bank_inner = (35, 110, 55)
    water = (40, 120, 195)
    water_dark = (25, 85, 150)
    shine = (170, 235, 255)

    # Banks
    pygame.draw.lines(tile, bank_outer, False, local_pts, width + 18)
    pygame.draw.lines(tile, bank_inner, False, local_pts, width + 10)
    # Water
    pygame.draw.lines(tile, water_dark, False, local_pts, width + 4)
    pygame.draw.lines(tile, water, False, local_pts, width)
    # Small highlight stripe
    pygame.draw.lines(tile, shine, False, local_pts, max(2, width // 5))


def _draw_mountain_tile(tile: pygame.Surface, center_world: pygame.Vector2, size: int, tile_world: pygame.Rect):
    cx = int(center_world.x - tile_world.left)
    cy = int(center_world.y - tile_world.top)

    base_w = int(size * 1.1)
    height = int(size * 1.5)
    left = (cx - base_w, cy + int(height * 0.55))
    right = (cx + base_w, cy + int(height * 0.55))
    peak = (cx, cy - height)

    main = (120, 120, 125)
    shade = (85, 85, 90)
    outline = (50, 50, 55)
    snow = (225, 235, 245)
    snow_edge = (170, 190, 205)

    pygame.draw.polygon(tile, shade, [(peak[0] + 10, peak[1] + 12), right, (cx + 8, cy + int(height * 0.55))])
    pygame.draw.polygon(tile, main, [peak, left, right])
    pygame.draw.polygon(tile, outline, [peak, left, right], 3)

    snow_h = int(height * 0.32)
    cap = [
        (peak[0], peak[1]),
        (peak[0] - int(base_w * 0.30), peak[1] + snow_h),
        (peak[0] + int(base_w * 0.25), peak[1] + snow_h + 10),
    ]
    pygame.draw.polygon(tile, snow, cap)
    pygame.draw.polygon(tile, snow_edge, cap, 2)


def get_field_house_rects(field_width: int, field_height: int) -> list[pygame.Rect]:
    """House footprint rects in field world coordinates (solid)."""
    anchor = _get_shop_village_anchor(field_width, field_height)
    shop_x = int(anchor.x)
    shop_y = int(anchor.y)

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
    # Place the boss arena between the shop village (top-left-ish) and the icy biome (top-right),
    # so the early quest destination reads clearly on the map.
    center = (int(field_width * 0.52), int(field_height * 0.17))
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


def get_field_farm_rects(field_width: int, field_height: int) -> list[pygame.Rect]:
    return [
        pygame.Rect(int(field_width * 0.52), int(field_height * 0.72), 360, 240),
        pygame.Rect(int(field_width * 0.72), int(field_height * 0.68), 380, 260),
    ]


def get_field_pond_rect(field_width: int, field_height: int) -> pygame.Rect:
    return pygame.Rect(int(field_width * 0.62), int(field_height * 0.32), 420, 260)


def get_field_ruins_rects(field_width: int, field_height: int) -> list[pygame.Rect]:
    """Non-solid decorative landmarks for the field and map."""
    base = pygame.Rect(0, 0, 420, 260)
    base.center = (int(field_width * 0.44), int(field_height * 0.44))
    inner = base.inflate(-120, -120)
    pillar = pygame.Rect(0, 0, 44, 44)
    pillar.center = (inner.left + 70, inner.top + 60)
    pillar2 = pygame.Rect(0, 0, 44, 44)
    pillar2.center = (inner.right - 70, inner.bottom - 60)
    return [base, inner, pillar, pillar2]


def get_field_shrine_rect(field_width: int, field_height: int) -> pygame.Rect:
    rect = pygame.Rect(0, 0, 220, 180)
    rect.center = (int(field_width * 0.18), int(field_height * 0.84))
    return rect


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

    # Shopkeeper/table area (matches get_room3_table_rect positioning)
    anchor = _get_shop_village_anchor(field_width, field_height)
    shop_x = int(anchor.x)
    shop_y = int(anchor.y)
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
    for r in get_field_farm_rects(field_width, field_height):
        _draw_farm(surface, r)

    # Small pond to break up the grass
    pond_rect = get_field_pond_rect(field_width, field_height)
    pygame.draw.ellipse(surface, (40, 110, 170), pond_rect)
    pygame.draw.ellipse(surface, (170, 220, 255), pond_rect.inflate(-18, -18), 4)
    pygame.draw.ellipse(surface, (20, 70, 120), pond_rect, 4)

    # Decorative ruins (non-solid landmark)
    ruins = get_field_ruins_rects(field_width, field_height)
    pygame.draw.rect(surface, (110, 110, 120), ruins[0], border_radius=14)
    pygame.draw.rect(surface, (70, 70, 80), ruins[0], 6, border_radius=14)
    pygame.draw.rect(surface, (90, 90, 100), ruins[1], border_radius=10)
    pygame.draw.rect(surface, (55, 55, 65), ruins[1], 4, border_radius=10)
    for pillar in ruins[2:]:
        pygame.draw.rect(surface, (120, 120, 130), pillar, border_radius=10)
        pygame.draw.rect(surface, (60, 60, 70), pillar, 3, border_radius=10)

    # Tiny shrine (non-solid landmark)
    shrine = get_field_shrine_rect(field_width, field_height)
    pygame.draw.rect(surface, (170, 170, 190), shrine, border_radius=12)
    pygame.draw.rect(surface, (90, 90, 110), shrine, 6, border_radius=12)
    roof = [
        (shrine.left - 14, shrine.top + 18),
        (shrine.centerx, shrine.top - 90),
        (shrine.right + 14, shrine.top + 18),
    ]
    pygame.draw.polygon(surface, (130, 90, 110), roof)
    pygame.draw.polygon(surface, (70, 50, 70), roof, 5)

    # Decorative trees and shrubs (deterministic)
    rng = random.Random(1337)
    density = (field_width * field_height) / (3200 * 2400)
    tree_count = max(110, int(110 * density))
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
        (field_width * 0.44, field_height * 0.18),
        (field_width * 0.78, field_height * 0.46),
    ]
    for rx, ry in rocks:
        pygame.draw.circle(surface, rock_shadow, (int(rx + 10), int(ry + 10)), 26)
        pygame.draw.circle(surface, rock_color, (int(rx), int(ry)), 26)
        pygame.draw.circle(surface, (180, 180, 180), (int(rx - 8), int(ry - 10)), 10)

    return surface


def get_field_environment_surface(field_width: int, field_height: int) -> pygame.Surface:
    # Legacy fallback for small fields only (the large field is rendered in tiles).
    if field_width * field_height > 40_000_000:
        tiny = pygame.Surface((1, 1))
        tiny.fill((58, 145, 62))
        return tiny
    key = (field_width, field_height)
    cached = _FIELD_MAP_CACHE.get((0, 0, field_width, field_height))
    if cached is None or cached.get_size() != (field_width, field_height):
        cached = build_field_environment_surface(field_width, field_height)
        _FIELD_MAP_CACHE[(0, 0, field_width, field_height)] = cached
    return cached


def _get_field_features(field_width: int, field_height: int) -> dict:
    key = (field_width, field_height)
    cached = _FIELD_FEATURE_CACHE.get(key)
    if cached is not None:
        return cached

    road_w = 120
    main_h = pygame.Rect(0, int(field_height * 0.58 - road_w / 2), field_width, road_w)
    main_v = pygame.Rect(int(field_width * 0.34 - road_w / 2), 0, road_w, field_height)

    anchor = _get_shop_village_anchor(field_width, field_height)
    shop_x = int(anchor.x)
    shop_y = int(anchor.y)
    house_rects = get_field_house_rects(field_width, field_height)

    plaza = _clamp_rect_in_bounds(pygame.Rect(shop_x - 260, shop_y - 260, 620, 460), field_width, field_height)
    for r in house_rects:
        plaza = plaza.union(r.inflate(160, 160))
    plaza = _clamp_rect_in_bounds(plaza, field_width, field_height)

    lane = _clamp_rect_in_bounds(
        pygame.Rect(shop_x - road_w // 2, shop_y, road_w, main_h.centery - shop_y + road_w // 2),
        field_width,
        field_height,
        margin=0,
    )
    lane_join = _clamp_rect_in_bounds(
        pygame.Rect(0, main_h.top, int(field_width * 0.22), main_h.height),
        field_width,
        field_height,
        margin=0,
    )

    arena = get_field_boss_arena_rect(field_width, field_height)
    arena_walls = get_field_boss_arena_wall_rects(field_width, field_height)
    arena_door = get_field_boss_arena_door_rect(field_width, field_height)

    farms = get_field_farm_rects(field_width, field_height)
    pond_rect = get_field_pond_rect(field_width, field_height)
    ruins = get_field_ruins_rects(field_width, field_height)
    shrine = get_field_shrine_rect(field_width, field_height)

    rng = random.Random((field_width * 97) ^ (field_height * 193) ^ 99173)

    # Rivers: a couple of gentle meanders for variety.
    rivers: list[dict] = []
    for axis in ("x", "y"):
        if axis == "x":
            base = field_height * rng.uniform(0.18, 0.32)
            amp1 = field_height * rng.uniform(0.020, 0.040)
            amp2 = field_height * rng.uniform(0.010, 0.020)
            f1 = 2 * math.pi / rng.uniform(8200, 12000)
            f2 = 2 * math.pi / rng.uniform(3400, 5200)
            ph1 = rng.uniform(0, 2 * math.pi)
            ph2 = rng.uniform(0, 2 * math.pi)
            step = 520
            pts: list[pygame.Vector2] = []
            for xx in range(0, field_width + step, step):
                yy = base + amp1 * math.sin(xx * f1 + ph1) + amp2 * math.sin(xx * f2 + ph2)
                pts.append(pygame.Vector2(xx, yy))
        else:
            base = field_width * rng.uniform(0.70, 0.86)
            amp1 = field_width * rng.uniform(0.018, 0.032)
            amp2 = field_width * rng.uniform(0.009, 0.016)
            f1 = 2 * math.pi / rng.uniform(7600, 10800)
            f2 = 2 * math.pi / rng.uniform(3200, 5200)
            ph1 = rng.uniform(0, 2 * math.pi)
            ph2 = rng.uniform(0, 2 * math.pi)
            step = 520
            pts = []
            for yy in range(0, field_height + step, step):
                xx = base + amp1 * math.sin(yy * f1 + ph1) + amp2 * math.sin(yy * f2 + ph2)
                pts.append(pygame.Vector2(xx, yy))

        width = int(rng.randrange(26, 44))
        min_x = min(p.x for p in pts) - (width + 50)
        max_x = max(p.x for p in pts) + (width + 50)
        min_y = min(p.y for p in pts) - (width + 50)
        max_y = max(p.y for p in pts) + (width + 50)
        rivers.append(
            {
                "points": pts,
                "width": width,
                "bounds": pygame.Rect(int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y)),
            }
        )

    # Mountains: a few clusters of peaks.
    mountain_peaks: list[dict] = []
    ranges = [
        pygame.Vector2(field_width * 0.10, field_height * 0.12),
        pygame.Vector2(field_width * 0.86, field_height * 0.14),
        pygame.Vector2(field_width * 0.18, field_height * 0.86),
    ]
    for center in ranges:
        for _ in range(rng.randrange(18, 28)):
            off = pygame.Vector2(rng.uniform(-1, 1), rng.uniform(-1, 1))
            if off.length_squared() > 0:
                off = off.normalize()
            off *= rng.uniform(140, 900)
            pos = center + off
            x = int(max(ENV_MARGIN, min(field_width - ENV_MARGIN, pos.x)))
            y = int(max(ENV_MARGIN, min(field_height - ENV_MARGIN, pos.y)))
            if abs(y - main_h.centery) < 220 or abs(x - main_v.centerx) < 220:
                continue
            if pond_rect.inflate(220, 220).collidepoint(x, y):
                continue
            if arena.inflate(520, 520).collidepoint(x, y):
                continue
            if plaza.inflate(260, 260).collidepoint(x, y) or lane.inflate(260, 260).collidepoint(x, y) or lane_join.inflate(260, 260).collidepoint(x, y):
                continue
            if shrine.inflate(220, 220).collidepoint(x, y):
                continue
            too_close_river = False
            for rv in rivers:
                if rv["bounds"].inflate(240, 240).collidepoint(x, y):
                    too_close_river = True
                    break
            if too_close_river:
                continue
            mountain_peaks.append({"pos": pygame.Vector2(x, y), "size": rng.randrange(36, 84)})

    features = {
        "road_w": road_w,
        "main_h": main_h,
        "main_v": main_v,
        "shop_x": shop_x,
        "shop_y": shop_y,
        "house_rects": house_rects,
        "plaza": plaza,
        "lane": lane,
        "lane_join": lane_join,
        "arena": arena,
        "arena_walls": arena_walls,
        "arena_door": arena_door,
        "farms": farms,
        "pond": pond_rect,
        "ruins": ruins,
        "shrine": shrine,
        "rivers": rivers,
        "mountains": mountain_peaks,
        "biomes": _get_field_biomes(field_width, field_height),
    }
    _FIELD_FEATURE_CACHE[key] = features
    return features


def _draw_grass_tile(tile: pygame.Surface, tile_world: pygame.Rect):
    grass_base = (58, 145, 62)
    grass_light = (76, 175, 80)
    tile.fill(grass_base)

    stripe_h = 10
    step = 40
    first = (-tile_world.top) % step
    for yy in range(first, tile.get_height(), step):
        pygame.draw.rect(tile, grass_light, pygame.Rect(0, yy, tile.get_width(), stripe_h))


def _apply_biomes_to_tile(
    tile: pygame.Surface,
    tile_world: pygame.Rect,
    *,
    field_width: int,
    field_height: int,
    biomes: dict,
    tile_rng: random.Random,
):
    w, h = tile.get_width(), tile.get_height()

    # Volcano palette.
    v_ash = (42, 38, 44)
    v_ash_dark = (28, 26, 30)
    v_lava = (255, 120, 40)
    v_lava_hot = (255, 190, 70)

    # Snow palette.
    s_base = (200, 232, 250)
    s_ice = (160, 210, 245)
    s_shadow = (120, 170, 210)

    # Volcano region overlay (bottom-left).
    if tile_world.colliderect(biomes["volcano_bbox"]):
        vw = int(biomes["volcano"]["w"])
        # Clip to the x range that can be inside the volcano biome.
        x_max_local = max(0, min(w, vw - tile_world.left))
        if x_max_local > 0:
            step = max(24, w // 18)
            boundary_pts: list[tuple[int, int]] = []
            for xl in range(0, x_max_local + 1, step):
                xw = tile_world.left + xl
                yb = _volcano_boundary_y(xw, field_width, field_height, biomes)
                yl = int(yb - tile_world.top)
                yl = max(0, min(h, yl))
                boundary_pts.append((xl, yl))
            if boundary_pts and boundary_pts[-1][0] != x_max_local:
                xl = x_max_local
                xw = tile_world.left + xl
                yb = _volcano_boundary_y(xw, field_width, field_height, biomes)
                yl = int(yb - tile_world.top)
                yl = max(0, min(h, yl))
                boundary_pts.append((xl, yl))

            poly = boundary_pts + [(x_max_local, h), (0, h)]
            pygame.draw.polygon(tile, v_ash, poly)
            if len(boundary_pts) >= 2:
                pygame.draw.lines(tile, v_ash_dark, False, boundary_pts, 5)

            # Rock specks.
            for _ in range(140):
                xl = tile_rng.randrange(0, x_max_local)
                yl = tile_rng.randrange(0, h)
                xw = tile_world.left + xl
                yw = tile_world.top + yl
                if not _is_in_volcano(xw, yw, field_width, field_height, biomes):
                    continue
                r = tile_rng.randrange(2, 6)
                col = (55, 50, 58) if tile_rng.random() < 0.6 else (32, 30, 34)
                pygame.draw.circle(tile, col, (xl, yl), r)

            # Lava cracks.
            def _draw_lava_crack(points: list[tuple[int, int]], base_w: int):
                if len(points) < 2:
                    return
                # Dark border, then lava core, then hot center highlight.
                pygame.draw.lines(tile, v_ash_dark, False, points, base_w + 6)
                pygame.draw.lines(tile, v_lava, False, points, base_w)
                pygame.draw.lines(tile, v_lava_hot, False, points, max(2, base_w // 2))
                # Rounded caps / little "pools".
                for (px, py) in points:
                    pygame.draw.circle(tile, v_lava, (px, py), max(2, base_w // 2))
                    pygame.draw.circle(tile, v_lava_hot, (px, py), max(2, base_w // 3))

            crack_count = 6
            for _ in range(crack_count):
                xl = tile_rng.randrange(0, x_max_local)
                yl = tile_rng.randrange(0, h)
                xw0 = tile_world.left + xl
                yw0 = tile_world.top + yl
                if not _is_in_volcano(xw0, yw0, field_width, field_height, biomes):
                    continue

                base_w = tile_rng.randrange(7, 11)
                segs = tile_rng.randrange(4, 7)
                step_len = tile_rng.randrange(int(min(w, h) * 0.05), int(min(w, h) * 0.11))
                ang = tile_rng.uniform(-1.35, -0.25)
                pts: list[tuple[int, int]] = [(xl, yl)]
                cur = pygame.Vector2(xl, yl)
                cur_ang = ang
                for _s in range(segs):
                    cur_ang += tile_rng.uniform(-0.55, 0.55)
                    nxt = cur + pygame.Vector2(math.cos(cur_ang), math.sin(cur_ang)) * step_len
                    nx = int(max(0, min(w - 1, nxt.x)))
                    ny = int(max(0, min(h - 1, nxt.y)))
                    xw = tile_world.left + nx
                    yw = tile_world.top + ny
                    if not _is_in_volcano(xw, yw, field_width, field_height, biomes):
                        break
                    if (nx, ny) != pts[-1]:
                        pts.append((nx, ny))
                    cur = pygame.Vector2(nx, ny)

                _draw_lava_crack(pts, base_w)

                # Occasional branch for extra shape.
                if len(pts) >= 4 and tile_rng.random() < 0.55:
                    bi = tile_rng.randrange(1, len(pts) - 2)
                    bx, by = pts[bi]
                    branch_ang = ang + tile_rng.uniform(-1.4, 1.4)
                    bpts: list[tuple[int, int]] = [(bx, by)]
                    cur = pygame.Vector2(bx, by)
                    for _s in range(tile_rng.randrange(2, 4)):
                        branch_ang += tile_rng.uniform(-0.45, 0.45)
                        nxt = cur + pygame.Vector2(math.cos(branch_ang), math.sin(branch_ang)) * (step_len * 0.75)
                        nx = int(max(0, min(w - 1, nxt.x)))
                        ny = int(max(0, min(h - 1, nxt.y)))
                        xw = tile_world.left + nx
                        yw = tile_world.top + ny
                        if not _is_in_volcano(xw, yw, field_width, field_height, biomes):
                            break
                        if (nx, ny) != bpts[-1]:
                            bpts.append((nx, ny))
                        cur = pygame.Vector2(nx, ny)
                    _draw_lava_crack(bpts, max(4, base_w - 3))

    # Snow region overlay (top-right).
    if tile_world.colliderect(biomes["snow_bbox"]):
        sh = int(biomes["snow"]["h"])
        y_max_local = max(0, min(h, sh - tile_world.top))
        if y_max_local > 0:
            step = max(24, h // 18)
            boundary_pts: list[tuple[int, int]] = []
            for yl in range(0, y_max_local + 1, step):
                yw = tile_world.top + yl
                xb = _snow_boundary_x(yw, field_width, field_height, biomes)
                xl = int(xb - tile_world.left)
                xl = max(0, min(w, xl))
                boundary_pts.append((xl, yl))
            if boundary_pts and boundary_pts[-1][1] != y_max_local:
                yl = y_max_local
                yw = tile_world.top + yl
                xb = _snow_boundary_x(yw, field_width, field_height, biomes)
                xl = int(xb - tile_world.left)
                xl = max(0, min(w, xl))
                boundary_pts.append((xl, yl))

            poly = boundary_pts + [(w, y_max_local), (w, 0)]
            pygame.draw.polygon(tile, s_base, poly)
            if len(boundary_pts) >= 2:
                pygame.draw.lines(tile, s_shadow, False, boundary_pts, 4)

            # Ice patches.
            for _ in range(22):
                xl = tile_rng.randrange(0, w)
                yl = tile_rng.randrange(0, y_max_local)
                xw = tile_world.left + xl
                yw = tile_world.top + yl
                if not _is_in_snow(xw, yw, field_width, field_height, biomes):
                    continue
                rw = tile_rng.randrange(18, 64)
                rh = tile_rng.randrange(12, 44)
                rect = pygame.Rect(xl - rw // 2, yl - rh // 2, rw, rh)
                pygame.draw.ellipse(tile, s_ice, rect)
                pygame.draw.ellipse(tile, s_shadow, rect, 2)

    # Center clearing (paint grass back over biomes so the middle stays open).
    if tile_world.colliderect(biomes["clear_bbox"]):
        c = biomes["clear"]
        cx = float(c["cx"])
        cy = float(c["cy"])
        rx = float(c["rx"])
        ry = float(c["ry"])
        clear_world = pygame.Rect(int(cx - rx), int(cy - ry), int(rx * 2), int(ry * 2))
        if tile_world.colliderect(clear_world):
            rect_local = clear_world.move(-tile_world.left, -tile_world.top)
            grass_base = (58, 145, 62)
            grass_light = (76, 175, 80)
            pygame.draw.ellipse(tile, grass_base, rect_local)
            pygame.draw.ellipse(tile, grass_light, rect_local.inflate(-24, -24), 2)


def _draw_tree_tile(surface: pygame.Surface, pos_world: pygame.Vector2, size: int, tile_world: pygame.Rect):
    local = pygame.Vector2(pos_world.x - tile_world.left, pos_world.y - tile_world.top)
    _draw_tree(surface, local, size)


def _get_field_tile_surface(field_width: int, field_height: int, tile_x: int, tile_y: int, tile_size: int = FIELD_TILE_SIZE) -> pygame.Surface:
    key = (field_width, field_height, tile_size, tile_x, tile_y)
    cached = _FIELD_TILE_CACHE.get(key)
    if cached is not None:
        _FIELD_TILE_CACHE.move_to_end(key)
        return cached

    tile_world = pygame.Rect(tile_x * tile_size, tile_y * tile_size, tile_size, tile_size)
    tile = pygame.Surface((tile_size, tile_size))
    _draw_grass_tile(tile, tile_world)

    f = _get_field_features(field_width, field_height)
    biomes = f.get("biomes")
    if biomes is not None:
        tile_rng = random.Random((tile_x * 92821) ^ (tile_y * 68917) ^ _biome_seed(field_width, field_height) ^ 7331)
        _apply_biomes_to_tile(
            tile,
            tile_world,
            field_width=field_width,
            field_height=field_height,
            biomes=biomes,
            tile_rng=tile_rng,
        )
    main_h: pygame.Rect = f["main_h"]
    main_v: pygame.Rect = f["main_v"]
    plaza: pygame.Rect = f["plaza"]
    lane: pygame.Rect = f["lane"]
    lane_join: pygame.Rect = f["lane_join"]
    pond_rect: pygame.Rect = f["pond"]
    arena: pygame.Rect = f["arena"]
    arena_walls: list[pygame.Rect] = f["arena_walls"]
    arena_door: pygame.Rect = f["arena_door"]

    def draw_rect(func, rect: pygame.Rect, *args, **kwargs):
        if not tile_world.colliderect(rect):
            return
        func(tile, rect.move(-tile_world.left, -tile_world.top), *args, **kwargs)

    draw_rect(_draw_road, main_h)
    draw_rect(_draw_road, main_v)

    if tile_world.colliderect(plaza):
        pr = plaza.move(-tile_world.left, -tile_world.top)
        pygame.draw.rect(tile, (130, 130, 140), pr, border_radius=12)
        pygame.draw.rect(tile, (80, 80, 90), pr, 6, border_radius=12)
    draw_rect(_draw_road, lane)
    draw_rect(_draw_road, lane_join)

    for i, r in enumerate(f["house_rects"]):
        if not tile_world.colliderect(r):
            continue
        roof = (160, 80, 80) if i % 2 == 0 else (140, 90, 60)
        _draw_house(tile, r.move(-tile_world.left, -tile_world.top), roof_color=roof)

    if tile_world.colliderect(arena):
        yard = arena.inflate(-72, -72).move(-tile_world.left, -tile_world.top)
        pygame.draw.rect(tile, (70, 90, 75), yard, border_radius=18)
        pygame.draw.rect(tile, (55, 70, 60), yard, 3, border_radius=18)
    wall_fill = (130, 130, 140)
    wall_edge = (80, 80, 90)
    for wall in arena_walls:
        if not tile_world.colliderect(wall):
            continue
        w = wall.move(-tile_world.left, -tile_world.top)
        pygame.draw.rect(tile, wall_fill, w)
        pygame.draw.rect(tile, wall_edge, w, 4)
    if tile_world.colliderect(arena_door):
        d = arena_door.move(-tile_world.left, -tile_world.top)
        pygame.draw.rect(tile, wall_edge, d.inflate(12, 8), 3)

    for r in f["farms"]:
        if not tile_world.colliderect(r):
            continue
        _draw_farm(tile, r.move(-tile_world.left, -tile_world.top))

    if tile_world.colliderect(pond_rect):
        pr = pond_rect.move(-tile_world.left, -tile_world.top)
        pygame.draw.ellipse(tile, (40, 110, 170), pr)
        pygame.draw.ellipse(tile, (170, 220, 255), pr.inflate(-18, -18), 4)
        pygame.draw.ellipse(tile, (20, 70, 120), pr, 4)

    ruins = f["ruins"]
    for idx, rr in enumerate(ruins):
        if not tile_world.colliderect(rr):
            continue
        rlocal = rr.move(-tile_world.left, -tile_world.top)
        if idx == 0:
            pygame.draw.rect(tile, (110, 110, 120), rlocal, border_radius=14)
            pygame.draw.rect(tile, (70, 70, 80), rlocal, 6, border_radius=14)
        elif idx == 1:
            pygame.draw.rect(tile, (90, 90, 100), rlocal, border_radius=10)
            pygame.draw.rect(tile, (55, 55, 65), rlocal, 4, border_radius=10)
        else:
            pygame.draw.rect(tile, (120, 120, 130), rlocal, border_radius=10)
            pygame.draw.rect(tile, (60, 60, 70), rlocal, 3, border_radius=10)

    shrine = f["shrine"]
    if tile_world.colliderect(shrine):
        s = shrine.move(-tile_world.left, -tile_world.top)
        pygame.draw.rect(tile, (170, 170, 190), s, border_radius=12)
        pygame.draw.rect(tile, (90, 90, 110), s, 6, border_radius=12)
        roof = [
            (s.left - 14, s.top + 18),
            (s.centerx, s.top - 90),
            (s.right + 14, s.top + 18),
        ]
        pygame.draw.polygon(tile, (130, 90, 110), roof)
        pygame.draw.polygon(tile, (70, 50, 70), roof, 5)

    # Rivers (decor)
    for rv in f.get("rivers", []):
        bounds: pygame.Rect = rv["bounds"]
        if not tile_world.colliderect(bounds):
            continue
        _draw_river_tile(tile, rv["points"], int(rv["width"]), tile_world)

    # Mountains (decor)
    for peak in f.get("mountains", []):
        p: pygame.Vector2 = peak["pos"]
        size = int(peak["size"])
        if not tile_world.collidepoint(p.x, p.y):
            # peaks are big; include if the base could be on-tile
            if not tile_world.inflate(size * 4, size * 4).collidepoint(p.x, p.y):
                continue
        _draw_mountain_tile(tile, p, size, tile_world)

    rng = random.Random((tile_x * 92821) ^ (tile_y * 68917) ^ (field_width * 37) ^ (field_height * 97) ^ 1337)
    rivers = f.get("rivers", [])
    mountains = f.get("mountains", [])
    tree_attempts = 10
    for _ in range(tree_attempts):
        x = rng.randrange(tile_world.left, tile_world.right)
        y = rng.randrange(tile_world.top, tile_world.bottom)
        if biomes is not None:
            if _in_center_clear(x, y, biomes) or _is_in_snow(x, y, field_width, field_height, biomes) or _is_in_volcano(
                x, y, field_width, field_height, biomes
            ):
                continue
        if abs(y - main_h.centery) < 120 or abs(x - main_v.centerx) < 120:
            continue
        if pond_rect.collidepoint(x, y):
            continue
        too_close_river = False
        for rv in rivers:
            if rv["bounds"].inflate(140, 140).collidepoint(x, y):
                too_close_river = True
                break
        if too_close_river:
            continue
        too_close_mountain = False
        for m in mountains:
            mp: pygame.Vector2 = m["pos"]
            if (mp.x - x) * (mp.x - x) + (mp.y - y) * (mp.y - y) < 240 * 240:
                too_close_mountain = True
                break
        if too_close_mountain:
            continue
        if arena.inflate(120, 120).collidepoint(x, y):
            continue
        if plaza.collidepoint(x, y) or lane.collidepoint(x, y) or lane_join.collidepoint(x, y):
            continue
        size = rng.randrange(26, 52)
        _draw_tree_tile(tile, pygame.Vector2(x, y), size, tile_world)

    rock_shadow = (80, 80, 80)
    rock_color = (120, 120, 120)
    for _ in range(1):
        rx = rng.randrange(tile_world.left, tile_world.right)
        ry = rng.randrange(tile_world.top, tile_world.bottom)
        if pond_rect.inflate(60, 60).collidepoint(rx, ry):
            continue
        if biomes is not None:
            if _is_in_snow(rx, ry, field_width, field_height, biomes):
                continue
        too_close_river = False
        for rv in rivers:
            if rv["bounds"].inflate(120, 120).collidepoint(rx, ry):
                too_close_river = True
                break
        if too_close_river:
            continue
        local = (int(rx - tile_world.left), int(ry - tile_world.top))
        pygame.draw.circle(tile, rock_shadow, (local[0] + 10, local[1] + 10), 20)
        pygame.draw.circle(tile, rock_color, local, 20)
        pygame.draw.circle(tile, (180, 180, 180), (local[0] - 6, local[1] - 8), 8)

    _FIELD_TILE_CACHE[key] = tile
    _FIELD_TILE_CACHE.move_to_end(key)
    while len(_FIELD_TILE_CACHE) > FIELD_TILE_CACHE_MAX:
        _FIELD_TILE_CACHE.popitem(last=False)
    return tile


def get_field_map_surface(target_size: tuple[int, int], field_width: int, field_height: int) -> pygame.Surface:
    """Scaled 'image' of the environment for the map overlay."""
    key = (target_size[0], target_size[1], field_width, field_height)
    cached = _FIELD_MAP_CACHE.get(key)
    if cached is not None:
        return cached
    surface = pygame.Surface(target_size)
    w, h = target_size
    grass_base = (58, 145, 62)
    grass_light = (76, 175, 80)
    surface.fill(grass_base)
    # light horizontal bands so the map isn't a flat green slab
    stripe_h = 3
    step = 18
    for yy in range(0, target_size[1], step):
        pygame.draw.rect(surface, grass_light, pygame.Rect(0, yy, target_size[0], stripe_h))

    biomes = _get_field_biomes(field_width, field_height)
    rng = random.Random(_biome_seed(field_width, field_height) ^ 9001)

    # Volcano biome (bottom-left).
    volcano = pygame.Surface((w, h), pygame.SRCALPHA)
    v_ash = (42, 38, 44)
    v_ash_dark = (28, 26, 30)
    v_lava = (255, 120, 40)
    v_lava_hot = (255, 190, 70)
    sx = w / float(field_width)
    sy = h / float(field_height)
    vw_world = float(biomes["volcano"]["w"])
    v_boundary: list[tuple[int, int]] = []
    for i in range(24):
        t = i / 23.0
        xw = t * vw_world
        yw = _volcano_boundary_y(xw, field_width, field_height, biomes)
        v_boundary.append((int(xw * sx), int(yw * sy)))
    v_poly = [(0, h), (0, int((field_height - float(biomes["volcano"]["h"])) * sy))] + v_boundary + [(int(vw_world * sx), h)]
    pygame.draw.polygon(volcano, v_ash, v_poly)
    pygame.draw.lines(volcano, v_ash_dark, False, v_boundary, 6)

    # Lava cracks (deterministic, within the biome)
    def _draw_map_lava_crack(points: list[tuple[int, int]], base_w: int):
        if len(points) < 2:
            return
        pygame.draw.lines(volcano, v_ash_dark, False, points, base_w + 5)
        pygame.draw.lines(volcano, v_lava, False, points, base_w)
        pygame.draw.lines(volcano, v_lava_hot, False, points, max(2, base_w // 2))
        for (px, py) in points:
            pygame.draw.circle(volcano, v_lava, (px, py), max(2, base_w // 2))
            pygame.draw.circle(volcano, v_lava_hot, (px, py), max(2, base_w // 3))

    for _ in range(10):
        x = rng.randrange(0, max(1, int(w * 0.36)))
        y = rng.randrange(max(0, int(h * 0.60)), h)
        if volcano.get_at((x, y)).a == 0:
            continue
        base_w = rng.randrange(6, 10)
        segs = rng.randrange(4, 7)
        step_len = rng.randrange(int(min(w, h) * 0.025), int(min(w, h) * 0.050))
        ang = rng.uniform(-1.35, -0.25)
        pts: list[tuple[int, int]] = [(x, y)]
        cur = pygame.Vector2(x, y)
        cur_ang = ang
        for _s in range(segs):
            cur_ang += rng.uniform(-0.55, 0.55)
            nxt = cur + pygame.Vector2(math.cos(cur_ang), math.sin(cur_ang)) * step_len
            nx = int(max(0, min(w - 1, nxt.x)))
            ny = int(max(0, min(h - 1, nxt.y)))
            if volcano.get_at((nx, ny)).a == 0:
                break
            if (nx, ny) != pts[-1]:
                pts.append((nx, ny))
            cur = pygame.Vector2(nx, ny)
        _draw_map_lava_crack(pts, base_w)

        if len(pts) >= 4 and rng.random() < 0.55:
            bi = rng.randrange(1, len(pts) - 2)
            bx, by = pts[bi]
            branch_ang = ang + rng.uniform(-1.4, 1.4)
            bpts: list[tuple[int, int]] = [(bx, by)]
            cur = pygame.Vector2(bx, by)
            for _s in range(rng.randrange(2, 4)):
                branch_ang += rng.uniform(-0.45, 0.45)
                nxt = cur + pygame.Vector2(math.cos(branch_ang), math.sin(branch_ang)) * (step_len * 0.85)
                nx = int(max(0, min(w - 1, nxt.x)))
                ny = int(max(0, min(h - 1, nxt.y)))
                if volcano.get_at((nx, ny)).a == 0:
                    break
                if (nx, ny) != bpts[-1]:
                    bpts.append((nx, ny))
                cur = pygame.Vector2(nx, ny)
            _draw_map_lava_crack(bpts, max(4, base_w - 2))

    # Rocky texture specks
    for _ in range(160):
        x = rng.randrange(0, int(w * 0.40))
        y = rng.randrange(int(h * 0.58), h)
        if volcano.get_at((x, y)).a == 0:
            continue
        r = rng.randrange(2, 6)
        col = (55, 50, 58) if rng.random() < 0.6 else (32, 30, 34)
        pygame.draw.circle(volcano, col, (x, y), r)

    surface.blit(volcano, (0, 0))

    # Snow/ice biome (top-right).
    snow = pygame.Surface((w, h), pygame.SRCALPHA)
    s_base = (200, 232, 250)
    s_ice = (160, 210, 245)
    s_shadow = (120, 170, 210)
    sh_world = float(biomes["snow"]["h"])
    s_boundary: list[tuple[int, int]] = []
    for i in range(22):
        t = i / 21.0
        yw = t * sh_world
        xw = _snow_boundary_x(yw, field_width, field_height, biomes)
        s_boundary.append((int(xw * sx), int(yw * sy)))
    s_poly = [(w, 0), (int((field_width - float(biomes["snow"]["w"])) * sx), 0)] + s_boundary + [(w, int(sh_world * sy))]
    pygame.draw.polygon(snow, s_base, s_poly)
    pygame.draw.lines(snow, s_shadow, False, s_boundary, 5)

    # Ice patches
    for _ in range(26):
        x = rng.randrange(max(0, int(w * 0.66)), w)
        y = rng.randrange(0, int(h * 0.32))
        if snow.get_at((x, y)).a == 0:
            continue
        rw = rng.randrange(18, 52)
        rh = rng.randrange(10, 34)
        rect = pygame.Rect(x - rw // 2, y - rh // 2, rw, rh)
        pygame.draw.ellipse(snow, s_ice, rect)
        pygame.draw.ellipse(snow, s_shadow, rect, 2)

    surface.blit(snow, (0, 0))

    # Wide open space in the middle: paint grass back over the biomes so it reads as a central plain.
    center = pygame.Vector2(int(biomes["clear"]["cx"] * sx), int(biomes["clear"]["cy"] * sy))
    clear_rect = pygame.Rect(0, 0, int((biomes["clear"]["rx"] * 2) * sx), int((biomes["clear"]["ry"] * 2) * sy))
    clear_rect.center = (int(center.x), int(center.y))
    pygame.draw.ellipse(surface, grass_base, clear_rect)
    pygame.draw.ellipse(surface, grass_light, clear_rect.inflate(-24, -24), 2)

    _FIELD_MAP_CACHE[key] = surface
    return surface


def blit_field_environment(screen: pygame.Surface, cam: pygame.Vector2, field_width: int, field_height: int):
    screen_w, screen_h = screen.get_width(), screen.get_height()
    tile_size = FIELD_TILE_SIZE
    start_x = max(0, int(cam.x) // tile_size)
    start_y = max(0, int(cam.y) // tile_size)
    end_x = min((field_width - 1) // tile_size, int((cam.x + screen_w) // tile_size) + 1)
    end_y = min((field_height - 1) // tile_size, int((cam.y + screen_h) // tile_size) + 1)

    for ty in range(start_y, end_y + 1):
        for tx in range(start_x, end_x + 1):
            tile = _get_field_tile_surface(field_width, field_height, tx, ty, tile_size=tile_size)
            screen.blit(tile, (tx * tile_size - int(cam.x), ty * tile_size - int(cam.y)))


def draw_background(
    screen: pygame.Surface,
    cam_offset: pygame.Vector2,
    level_index: int,
    field_width: int = settings.FIELD_WORLD_WIDTH,
    field_height: int = settings.FIELD_WORLD_HEIGHT,
):
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
    # Table sits in the overworld village near the shopkeeper.
    t_center = _get_shop_village_anchor(settings.FIELD_WORLD_WIDTH, settings.FIELD_WORLD_HEIGHT)
    return pygame.Rect(
        int(t_center.x - table_w / 2 + cam_offset.x),
        int(t_center.y - table_h / 2 + cam_offset.y),
        table_w,
        table_h,
    )


def get_shopkeeper_rect(screen: pygame.Surface) -> pygame.Rect:
    """Rectangle for the shopkeeper standing behind the table."""
    t_rect = get_room3_table_rect(screen, pygame.Vector2(0, 0))
    w = int(settings.NPC_WIDTH * 1.15)
    h = int(settings.NPC_HEIGHT * 1.15)
    rect = pygame.Rect(0, 0, w, h)
    rect.midbottom = (t_rect.centerx, t_rect.top - 6)
    return rect
