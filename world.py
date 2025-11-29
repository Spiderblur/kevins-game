import pygame

import settings


def draw_background(screen: pygame.Surface, cam_offset: pygame.Vector2, level_index: int, field_width=3200, field_height=2400):
    if level_index == 3:
        grass_base = (58, 145, 62)
        grass_light = (76, 175, 80)
        pad = 60
        bg_rect = pygame.Rect(
            -pad + int(cam_offset.x),
            -pad + int(cam_offset.y),
            field_width + pad * 2,
            field_height + pad * 2,
        )
        pygame.draw.rect(screen, grass_base, bg_rect)
        stripe_h = 12
        step = 44
        y_start = -pad
        y_end = field_height + pad
        for yy in range(y_start, y_end, step):
            stripe = pygame.Rect(
                -pad + int(cam_offset.x),
                yy + int(cam_offset.y),
                field_width + pad * 2,
                stripe_h,
            )
            pygame.draw.rect(screen, grass_light, stripe)
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
    t_center = pygame.Vector2(screen.get_width() * 0.68, screen.get_height() * 0.60)
    return pygame.Rect(
        int(t_center.x - table_w / 2 + cam_offset.x),
        int(t_center.y - table_h / 2 + cam_offset.y),
        table_w,
        table_h,
    )
