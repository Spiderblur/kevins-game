import pygame

# Player class and functions for movement, health, and drawing

class Player:
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
        self.is_blocking = False
        self.shield_blocks_left = 5
        self.is_drinking_potion = False
        self.potion_timer = 0.0
        self.potion_count = 1

    def move(self, move_vec, speed, dt):
        if move_vec.length_squared() > 0:
            move_vec = move_vec.normalize()
            self.pos += move_vec * speed * dt

    # Add more player methods as needed
