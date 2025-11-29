import pygame


def clamp(val, min_val, max_val):
    return max(min_val, min(val, max_val))


def circle_rect(center: pygame.Vector2, radius: float):
    return pygame.Rect(center.x - radius, center.y - radius, radius * 2, radius * 2)
