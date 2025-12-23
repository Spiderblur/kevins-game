import pygame


def clamp(val, min_val, max_val):
    return max(min_val, min(val, max_val))


def circle_rect(center: pygame.Vector2, radius: float):
    return pygame.Rect(center.x - radius, center.y - radius, radius * 2, radius * 2)


def line_of_sight_clear(a: pygame.Vector2, b: pygame.Vector2, blockers: list[pygame.Rect]) -> bool:
    """Return True if segment a->b does not intersect any blocker rect."""
    if not blockers:
        return True
    ax, ay = int(a.x), int(a.y)
    bx, by = int(b.x), int(b.y)
    for rect in blockers:
        if rect.clipline(ax, ay, bx, by):
            return False
    return True
