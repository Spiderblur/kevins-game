import pygame

# World and level functions (background, doors, coins, etc.)

def draw_background(screen, cam_offset, level_index, field_width=3200, field_height=2400):
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

# Add more world/level functions as needed
