import pygame

# Pig (enemy) class and functions

class Pig:
    def __init__(self, pos, radius, max_health):
        self.pos = pygame.Vector2(pos)
        self.radius = radius
        self.max_health = max_health
        self.health = max_health
        self.facing = pygame.Vector2(1, 0)
        self.sword_timer = 0.0
        self.cooldown = 0.0
        self.swing_base_dir = pygame.Vector2(1, 0)
        self.knockback_timer = 0.0
        self.knockback_vec = pygame.Vector2(0, 0)
        self.coin_dropped = False

    # Add more pig methods as needed
