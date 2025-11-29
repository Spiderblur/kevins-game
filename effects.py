from __future__ import annotations

import random

import pygame

import settings


def spawn_blood_splatter(center: pygame.Vector2, blood_splats: list) -> None:
    """Add a ring of outline circles around a hit point."""
    count = random.randint(8, 14)
    pts = []
    for _ in range(count):
        angle_deg = random.uniform(0, 360)
        dir_vec = pygame.Vector2(1, 0).rotate(angle_deg)
        dist = random.uniform(8, 26)
        pos = pygame.Vector2(center) + dir_vec * dist
        radius = random.uniform(2, 5)
        pts.append((pos, radius))
    blood_splats.append({"points": pts, "timer": settings.BLOOD_LIFETIME})
