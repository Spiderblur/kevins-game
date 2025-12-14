from __future__ import annotations

import math

import pygame

import settings


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def swing_ease(swing_timer: float, total_time: float) -> float:
    """Return a smooth 0..1 eased phase for the swing progress."""
    if swing_timer <= 0 or total_time <= 0:
        return 0.0
    raw_phase = 1.0 - _clamp01(swing_timer / total_time)
    # smootherstep for gentle acceleration and deceleration
    return raw_phase * raw_phase * raw_phase * (raw_phase * (raw_phase * 6 - 15) + 10)


def swing_reach_multiplier(swing_timer: float, total_time: float, min_reach: float = 0.65, max_reach: float = 1.0) -> float:
    """Scale how far the sword extends during a swing; starts shorter and reaches full extension mid-swing."""
    eased = swing_ease(swing_timer, total_time)
    return min_reach + (max_reach - min_reach) * eased


def get_sword_segment(center: pygame.Vector2, facing_vec: pygame.Vector2, extend_distance: float, length: float):
    f = pygame.Vector2(facing_vec)
    if f.length_squared() == 0:
        return center, center
    f = f.normalize()
    start = center + f * extend_distance
    end = start + f * length
    return start, end


def sword_polygon_points(center: pygame.Vector2, facing_vec: pygame.Vector2, extend_distance: float, length: float, width: float):
    start, end = get_sword_segment(center, facing_vec, extend_distance, length)
    f = end - start
    if f.length_squared() == 0:
        return [start, start, start, start]
    f = f.normalize()
    n = pygame.Vector2(-f.y, f.x) * (width / 2)
    p1 = start + n
    p2 = start - n
    p3 = end - n
    p4 = end + n
    return [p1, p2, p3, p4]


def get_swing_dir(base_dir: pygame.Vector2, swing_timer: float, total_time: float, fallback_dir: pygame.Vector2):
    if swing_timer <= 0 or total_time <= 0:
        return fallback_dir
    phase = swing_ease(swing_timer, total_time)
    start_angle = -settings.SWING_ARC_DEG / 2
    angle = start_angle + settings.SWING_ARC_DEG * phase
    b = pygame.Vector2(base_dir)
    if b.length_squared() == 0:
        b = pygame.Vector2(fallback_dir)
    return b.rotate(angle)


def point_segment_distance(p: pygame.Vector2, a: pygame.Vector2, b: pygame.Vector2):
    ab = b - a
    ab_len_sq = ab.length_squared()
    if ab_len_sq == 0:
        return (p - a).length()
    t = max(0, min(1, (p - a).dot(ab) / ab_len_sq))
    closest = a + ab * t
    return (p - closest).length()


def deal_damage_if_hit(
    attacker_pos: pygame.Vector2,
    attack_dir: pygame.Vector2,
    target_pos: pygame.Vector2,
    target_radius: float,
    swing_timer: float,
    swing_time: float,
    damage: int,
    extend_distance: float,
    length: float,
    sword_width: float,
):
    if swing_timer <= 0:
        return 0
    reach_mult = swing_reach_multiplier(swing_timer, swing_time)
    sword_a, sword_b = get_sword_segment(
        attacker_pos, attack_dir, extend_distance * reach_mult, length * reach_mult
    )
    dist = point_segment_distance(target_pos, sword_a, sword_b)
    return damage if dist <= (target_radius + sword_width / 2) else 0
