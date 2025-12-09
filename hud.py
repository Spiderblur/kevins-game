import pygame

import settings


def draw_player_health_bar_topleft(screen: pygame.Surface, current: int, maximum: int, x=10, y=10):
    bar_width = 80
    bar_height = 10
    pygame.draw.rect(screen, (100, 100, 100), (x, y, bar_width, bar_height))
    ratio = max(0, current) / maximum if maximum > 0 else 0
    pygame.draw.rect(screen, (255, 0, 0), (x, y, int(bar_width * ratio), bar_height))


def draw_player_stamina_bar_topleft(screen: pygame.Surface, current: float, maximum: float, x=10, y=24):
    bar_width = 80
    bar_height = 8
    pygame.draw.rect(screen, (70, 70, 70), (x, y, bar_width, bar_height))
    ratio = max(0.0, current) / maximum if maximum > 0 else 0
    pygame.draw.rect(screen, (50, 200, 80), (x, y, int(bar_width * ratio), bar_height))


def draw_health_bar_above(screen: pygame.Surface, center_pos: pygame.Vector2, current: int, maximum: int):
    bar_width = 80
    bar_height = 10
    x = center_pos.x - bar_width // 2
    y = center_pos.y - (settings.PIG_RADIUS + 28)
    pygame.draw.rect(screen, (100, 100, 100), (x, y, bar_width, bar_height))
    ratio = max(0, current) / maximum if maximum > 0 else 0
    pygame.draw.rect(screen, (255, 0, 0), (x, y, int(bar_width * ratio), bar_height))


def draw_coin_icon(screen: pygame.Surface, x: int, y: int, enabled=True):
    outline = (90, 70, 0)
    fill = (255, 215, 0) if enabled else (140, 140, 140)
    center = (x + 8, y + 8)
    pygame.draw.circle(screen, outline, center, 10)
    pygame.draw.circle(screen, fill, center, 8)
    pygame.draw.line(screen, outline, (center[0] - 2, center[1] - 6), (center[0] - 2, center[1] + 6), 2)
    pygame.draw.line(screen, outline, (center[0] + 2, center[1] - 6), (center[0] + 2, center[1] + 6), 2)


def draw_potion_icon(screen: pygame.Surface, x: int, y: int, enabled=True):
    """Draw a tiny potion bottle. enabled can be True/False or a mode string ('heal'/'speed')."""
    # Glass color
    glass = (200, 230, 255) if enabled else (120, 120, 120)
    if enabled == "heal":
        liquid = (220, 50, 50)
    elif enabled == "speed":
        liquid = (50, 120, 255)
    else:
        liquid = (90, 90, 90) if not enabled else (160, 220, 255)
    outline = (40, 40, 40)

    body_rect = pygame.Rect(x, y + 6, 14, 14)
    pygame.draw.rect(screen, glass, body_rect)
    liquid_rect = pygame.Rect(x + 2, y + 12, 10, 6)
    pygame.draw.rect(screen, liquid, liquid_rect)
    neck_rect = pygame.Rect(x + 4, y + 2, 6, 4)
    cap_rect = pygame.Rect(x + 3, y, 8, 2)
    pygame.draw.rect(screen, glass, neck_rect)
    pygame.draw.rect(screen, outline, cap_rect)
    pygame.draw.rect(screen, outline, body_rect, 1)
    pygame.draw.rect(screen, outline, neck_rect, 1)
