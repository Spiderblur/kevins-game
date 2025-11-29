import math
import sys
from typing import List

import pygame

import settings
from combat import deal_damage_if_hit, get_swing_dir, sword_polygon_points
from effects import spawn_blood_splatter
from game_state import GameState, create_game_state
from hud import (
    draw_coin_icon,
    draw_health_bar_above,
    draw_player_health_bar_topleft,
    draw_potion_icon,
)
from pig import spawn_pigs
from world import get_door_rect, get_room3_table_rect, get_shopkeeper_rect

DIALOGUE_BOX_PADDING = 10
DIALOGUE_BUTTON_PADDING = 6


def start_dialogue(state: GameState, lines: List[str]):
    """Begin showing dialogue lines with typewriter reveal."""
    state.dialogue_lines = list(lines)
    state.dialogue_index = 0
    state.dialogue_start_time = pygame.time.get_ticks() / 1000.0


def current_dialogue_text(state: GameState):
    if not state.dialogue_lines or state.dialogue_index >= len(state.dialogue_lines):
        return None
    return state.dialogue_lines[state.dialogue_index]


def dialogue_reveal(state: GameState):
    """Return (shown_text, is_full) for current dialogue line."""
    line = current_dialogue_text(state)
    if line is None:
        return "", True
    now = pygame.time.get_ticks() / 1000.0
    elapsed = max(0.0, now - state.dialogue_start_time)
    chars = int(elapsed * settings.DIALOGUE_CHARS_PER_SEC)
    if chars >= len(line):
        return line, True
    return line[:chars], False


def handle_dialogue_click(state: GameState):
    """Advance dialogue: finish reveal or go to next line."""
    line = current_dialogue_text(state)
    if line is None:
        return
    shown, full = dialogue_reveal(state)
    now = pygame.time.get_ticks() / 1000.0
    if not full:
        # Instantly finish this line
        state.dialogue_start_time = now - (len(line) / settings.DIALOGUE_CHARS_PER_SEC)
        return
    if state.dialogue_index + 1 < len(state.dialogue_lines):
        state.dialogue_index += 1
        state.dialogue_start_time = now
    else:
        state.dialogue_lines = []
        state.dialogue_index = 0
        state.dialogue_start_time = 0.0


def draw_dialogue(state: GameState):
    """Draw the current dialogue with a simple typewriter reveal and a prompt button."""
    line = current_dialogue_text(state)
    if line is None or state.font is None:
        return
    shown, full = dialogue_reveal(state)
    screen = state.screen
    text_surf = state.font.render(shown, True, (255, 255, 200))
    box_rect = text_surf.get_rect()
    box_rect.inflate_ip(DIALOGUE_BOX_PADDING * 2, DIALOGUE_BOX_PADDING * 2)
    box_rect.centerx = screen.get_width() // 2
    box_rect.top = 20
    pygame.draw.rect(screen, (30, 30, 60), box_rect)
    pygame.draw.rect(screen, (200, 200, 255), box_rect, 2)
    text_pos = (
        box_rect.centerx - text_surf.get_width() // 2,
        box_rect.top + DIALOGUE_BOX_PADDING,
    )
    screen.blit(text_surf, text_pos)

    # Button-like prompt below the box
    prompt_text = "Click text to continue"
    prompt_surf = state.font.render(prompt_text, True, (255, 255, 255) if full else (180, 180, 180))
    prompt_rect = prompt_surf.get_rect()
    prompt_rect.centerx = box_rect.centerx
    prompt_rect.top = box_rect.bottom + DIALOGUE_BUTTON_PADDING
    back_rect = prompt_rect.inflate(12, 8)
    pygame.draw.rect(screen, (40, 40, 70), back_rect)
    pygame.draw.rect(screen, (150, 150, 200), back_rect, 2)
    screen.blit(prompt_surf, prompt_rect)


def reset_round(state: GameState):
    """Reset positions, health, enemies, and timers for the current level."""
    player = state.player
    player.health = player.max_health
    player.speed = settings.PLAYER_BASE_SPEED
    player.swing_timer = 0.0
    player.cooldown = 0.0
    player.is_blocking = False
    player.shield_blocks_left = settings.SHIELD_MAX_BLOCKS
    player.potion_count = settings.START_POTION_COUNT
    player.is_drinking_potion = False
    player.potion_timer = 0.0
    player.armor_equipped = state.leather_armor_bought
    player.is_dodging = False
    player.dodge_timer = 0.0
    player.dodge_cooldown = 0.0
    player.knockback_timer = 0.0
    player.knockback_vec.update(0, 0)
    state.coin_count = 10
    state.dialogue_lines = []
    state.dialogue_index = 0
    state.dialogue_start_time = 0.0

    # Start near the shopkeeper/table to save time
    t_rect = get_room3_table_rect(state.screen, pygame.Vector2(0, 0))
    player.pos.update(t_rect.centerx - 80, t_rect.bottom + player.radius)

    state.coin_pickups.clear()
    state.blood_splats.clear()
    state.shake_timer = 0.0
    state.game_over = False
    state.door_revealed = False

    # Spawn pigs for the level
    if state.level_index <= 1:
        n = 1
    elif state.level_index == 2:
        n = 2
    else:
        n = 0
    state.pigs = spawn_pigs(n, state.level_index, state.screen)


def handle_death_screen(state: GameState, events: list[pygame.event.Event]):
    """Draw and manage the death menu (continue/exit)."""
    for event in events:
        if event.type == pygame.QUIT:
            state.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_c, pygame.K_RETURN, pygame.K_SPACE):
                reset_round(state)
            elif event.key in (pygame.K_ESCAPE, pygame.K_e):
                state.running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Handled after buttons are placed
            pass

    screen = state.screen
    screen.fill((0, 0, 0))
    title_font = pygame.font.SysFont(None, 120)
    menu_font = pygame.font.SysFont(None, 48)
    death_text = title_font.render("YOU DIED!", True, (255, 0, 0))
    death_rect = death_text.get_rect(center=(screen.get_width() / 2, screen.get_height() / 2 - 40))
    cont_text = menu_font.render("Continue", True, (255, 255, 255))
    exit_text = menu_font.render("Exit", True, (255, 255, 255))
    cont_rect = cont_text.get_rect(center=(screen.get_width() / 2, screen.get_height() / 2 + 20))
    exit_rect = exit_text.get_rect(center=(screen.get_width() / 2, screen.get_height() / 2 + 70))

    for event in events:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if cont_rect.collidepoint(event.pos):
                reset_round(state)
            elif exit_rect.collidepoint(event.pos):
                state.running = False

    screen.blit(death_text, death_rect)
    screen.blit(cont_text, cont_rect)
    screen.blit(exit_text, exit_rect)
    pygame.display.flip()
    state.dt = state.clock.tick(settings.TARGET_FPS) / 1000


def handle_events(state: GameState, events: list[pygame.event.Event]):
    player = state.player
    if state.map_open:
        for event in events:
            if event.type == pygame.QUIT:
                state.running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                state.map_open = False
        return
    for event in events:
        if event.type == pygame.QUIT:
            state.running = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if state.dialogue_lines:
                handle_dialogue_click(state)
                continue
            if state.level_index >= 3:
                npc_rect = get_shopkeeper_rect(state.screen)
                if npc_rect.collidepoint(event.pos):
                    state.shopkeeper_greeted = True
                    state.has_map = True
                    state.map_open = False
                    if not state.map_tested:
                        start_dialogue(
                            state,
                            [
                                "Shopkeeper: \"You look new. Here's a free map!\"",
                                "Shopkeeper: \"Why dont you try and use it?\"",
                            ],
                        )
                    else:
                        start_dialogue(
                            state,
                            [
                                "Shopkeeper: \"Did you hear the rumor about the possessed creatures?\"",
                                "Shopkeeper: \"Mladolr, the evil king, has been turning good creatures to bad.\"",
                            ],
                        )
                    return
            if (
                player.health > 0
                and player.cooldown <= 0
                and player.swing_timer <= 0
                and not player.is_blocking
                and not player.is_drinking_potion
            ):
                player.swing_timer = settings.PLAYER_SWING_TIME
                player.cooldown = settings.PLAYER_COOLDOWN
                if player.facing.length_squared() > 0:
                    player.swing_base_dir = player.facing.normalize()
                else:
                    player.swing_base_dir = pygame.Vector2(1, 0)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if player.health > 0 and player.shield_blocks_left > 0:
                player.is_blocking = True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            player.is_blocking = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
            if (
                player.potion_count > 0
                and player.health > 0
                and player.health < player.max_health
                and not player.is_drinking_potion
            ):
                player.is_drinking_potion = True
                player.potion_timer = 1.0
        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            if state.level_index >= 3 and not state.leather_armor_bought:
                t_rect = get_room3_table_rect(state.screen, pygame.Vector2(0, 0))
                near_rect = t_rect.inflate(settings.PLAYER_RADIUS * 2, settings.PLAYER_RADIUS * 2)
                if near_rect.collidepoint(player.pos.x, player.pos.y) and state.coin_count >= settings.SPEED_POTION_COST:
                    state.coin_count -= settings.SPEED_POTION_COST
                    state.leather_armor_bought = True
                    player.armor_equipped = True
        if state.inventory_open and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_x, mouse_y = event.pos
            slot_w, slot_h = 60, 60
            margin = 10
            inv_x = state.screen.get_width() // 2 - (slot_w * 5 + margin * 4) // 2
            inv_y = 120
            for i in range(settings.INVENTORY_SLOTS):
                x = inv_x + i * (slot_w + margin)
                y = inv_y
                rect = pygame.Rect(x, y, slot_w, slot_h)
                if rect.collidepoint(mouse_x, mouse_y) and state.inventory[i] == "Speed Potion":
                    player.speed = int(settings.PLAYER_BASE_SPEED * settings.SPEED_BOOST_MULT)
                    state.inventory[i] = ""
                    break
        if event.type == pygame.KEYDOWN and event.key == pygame.K_t:
            state.inventory_open = not state.inventory_open
        if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
            start_dodge(player)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            if state.has_map:
                state.map_open = not state.map_open
                if state.map_open:
                    state.map_tested = True
                    if state.shopkeeper_greeted:
                        start_dialogue(
                            state,
                            [
                                "Shopkeeper: \"Did you hear the rumor about the possessed creatures?\"",
                                "Shopkeeper: \"Mladolr, the evil king, has been turning good creatures to bad.\"",
                            ],
                        )


def start_dodge(player):
    """Start a quick dodge if ready."""
    if player.health <= 0 or player.is_dodging or player.dodge_cooldown > 0:
        return
    dir_vec = pygame.Vector2(player.facing)
    if dir_vec.length_squared() == 0:
        dir_vec = pygame.Vector2(1, 0)
    player.dodge_dir = dir_vec.normalize()
    player.is_dodging = True
    player.dodge_timer = settings.DODGE_DURATION
    player.dodge_cooldown = settings.DODGE_COOLDOWN


def update_game(state: GameState):
    player = state.player
    keys = pygame.key.get_pressed()
    if state.map_open:
        return
    if player.health > 0:
        move = pygame.Vector2(0, 0)
        if keys[pygame.K_w]:
            move.y -= 1
        if keys[pygame.K_s]:
            move.y += 1
        if keys[pygame.K_a]:
            move.x -= 1
        if keys[pygame.K_d]:
            move.x += 1
        if player.is_dodging:
            player.pos += player.dodge_dir * player.speed * settings.DODGE_SPEED_MULT * state.dt
            player.dodge_timer -= state.dt
            if player.dodge_timer <= 0:
                player.is_dodging = False
        else:
            if move.length_squared() > 0:
                move = move.normalize()
                player.pos += move * player.speed * state.dt

        if player.knockback_timer > 0:
            player.pos += player.knockback_vec * (settings.KNOCKBACK_SPEED * state.dt)
            player.knockback_timer -= state.dt

        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        to_mouse = mouse_pos - player.pos
        if to_mouse.length_squared() > 0:
            player.facing = to_mouse.normalize()

    for pig in state.pigs:
        if pig.health <= 0:
            continue
        to_player = player.pos - pig.pos
        dist = to_player.length()
        if dist > 0:
            pig.facing = to_player / dist
        if dist < state.chase_range and dist > 0:
            pig.pos += pig.facing * state.pig_speed * state.dt
            if dist < (settings.PIG_RADIUS + settings.PLAYER_RADIUS + settings.SWORD_LENGTH * 0.6):
                if pig.cooldown <= 0 and pig.swing_timer <= 0:
                    pig.swing_timer = settings.PIG_SWING_TIME
                    pig.cooldown = settings.PIG_COOLDOWN
                    pig.swing_base_dir = pig.facing.copy()

        if pig.knockback_timer > 0:
            pig.pos += pig.knockback_vec * (settings.KNOCKBACK_SPEED * state.dt)
            pig.knockback_timer -= state.dt

    if player.swing_timer > 0:
        player.swing_timer -= state.dt
    if player.cooldown > 0:
        player.cooldown -= state.dt

    for pig in state.pigs:
        if pig.swing_timer > 0:
            pig.swing_timer -= state.dt
            if pig.swing_timer < 0:
                pig.swing_timer = 0
        if pig.cooldown > 0:
            pig.cooldown -= state.dt
            if pig.cooldown < 0:
                pig.cooldown = 0

    if player.is_drinking_potion:
        player.potion_timer -= state.dt
        if player.potion_timer <= 0:
            player.health = min(player.max_health, player.health + settings.POTION_HEAL)
            player.potion_count -= 1
            player.is_drinking_potion = False
    if player.dodge_cooldown > 0:
        player.dodge_cooldown -= state.dt
        if player.dodge_cooldown < 0:
            player.dodge_cooldown = 0

    if state.shake_timer > 0:
        state.shake_timer -= state.dt
        if state.shake_timer < 0:
            state.shake_timer = 0

    if state.blood_splats:
        keep = []
        for s in state.blood_splats:
            s["timer"] -= state.dt
            if s["timer"] > 0:
                keep.append(s)
        state.blood_splats = keep

    if player.health > 0:
        for pig in state.pigs:
            if pig.health <= 0:
                continue
            player_attack_dir = (
                get_swing_dir(player.swing_base_dir, player.swing_timer, settings.PLAYER_SWING_TIME, player.facing)
                if player.swing_timer > 0
                else player.facing
            )
            dmg_to_pig = deal_damage_if_hit(
                player.pos,
                player_attack_dir,
                pig.pos,
                settings.PIG_RADIUS,
                player.swing_timer,
                settings.PLAYER_SWING_TIME,
                settings.PLAYER_DAMAGE,
                settings.PLAYER_SWING_DISTANCE,
                settings.SWORD_LENGTH,
                settings.SWORD_WIDTH,
            )
            if dmg_to_pig:
                pig.health = max(0, pig.health - dmg_to_pig)
                player.swing_timer = 0
                dir_vec = pig.pos - player.pos
                if dir_vec.length_squared() > 0:
                    pig.knockback_vec = dir_vec.normalize()
                    pig.knockback_timer = settings.KNOCKBACK_DURATION
                state.shake_timer = max(state.shake_timer, settings.SHAKE_DURATION)
                spawn_blood_splatter(pig.pos, state.blood_splats)
                if pig.health == 0 and not pig.coin_dropped:
                    state.coin_pickups.append({"pos": pig.pos.copy(), "value": settings.COIN_VALUE})
                    pig.coin_dropped = True

        if state.level_index < 3:
            if state.pigs and not state.door_revealed and all(p.health <= 0 for p in state.pigs):
                state.door_revealed = True
        else:
            state.door_revealed = False

    if player.health > 0:
        for pig in state.pigs:
            if pig.health <= 0:
                continue
            pig_attack_dir = (
                get_swing_dir(pig.swing_base_dir, pig.swing_timer, settings.PIG_SWING_TIME, pig.facing)
                if pig.swing_timer > 0
                else pig.facing
            )
            dmg_to_player = deal_damage_if_hit(
                pig.pos,
                pig_attack_dir,
                player.pos,
                settings.PLAYER_RADIUS,
                pig.swing_timer,
                settings.PIG_SWING_TIME,
                settings.PIG_DAMAGE,
                settings.PIG_SWING_DISTANCE,
                settings.SWORD_LENGTH,
                settings.SWORD_WIDTH,
            )
            if dmg_to_player:
                if player.is_dodging:
                    dmg_to_player = 0
                elif player.is_blocking:
                    pig.swing_timer = 0
                    if player.shield_blocks_left > 0:
                        player.shield_blocks_left -= 1
                    if player.shield_blocks_left <= 0:
                        player.is_blocking = False
                else:
                    if state.leather_armor_bought or player.armor_equipped:
                        dmg_to_player = int(dmg_to_player * 0.95)
                    player.health = max(0, player.health - dmg_to_player)
                    pig.swing_timer = 0
                    dir_vec = player.pos - pig.pos
                    if dir_vec.length_squared() > 0:
                        player.knockback_vec = dir_vec.normalize()
                        player.knockback_timer = settings.KNOCKBACK_DURATION
                    state.shake_timer = max(state.shake_timer, settings.SHAKE_DURATION)
                    spawn_blood_splatter(player.pos, state.blood_splats)
                    if player.health == 0:
                        player.is_blocking = False
                        state.game_over = True

    if state.coin_pickups and player.health > 0:
        remaining = []
        for coin in state.coin_pickups:
            if (player.pos - coin["pos"]).length() <= settings.COIN_PICKUP_RADIUS:
                state.coin_count += coin["value"]
            else:
                remaining.append(coin)
        state.coin_pickups = remaining

    if state.door_revealed and player.health > 0:
        door = get_door_rect(state.level_index, state.screen)
        enter_rect = door.inflate(settings.PLAYER_RADIUS * 2, settings.PLAYER_RADIUS * 2)
        if enter_rect.collidepoint(player.pos.x, player.pos.y):
            state.level_index += 1
            reset_round(state)
            state.door_revealed = False
            player.pos.update(settings.PLAYER_RADIUS + 20, state.screen.get_height() / 2)


def draw_game(state: GameState):
    screen = state.screen
    player = state.player
    keys = pygame.key.get_pressed()

    if state.level_index != 3:
        bg_gray = (120, 120, 120)
        screen.fill(bg_gray)
        rock_color = (100, 100, 100)
        rock_highlight = (180, 180, 180)
        rock_positions = [
            (screen.get_width() * 0.2, screen.get_height() * 0.7),
            (screen.get_width() * 0.5, screen.get_height() * 0.3),
            (screen.get_width() * 0.8, screen.get_height() * 0.6),
        ]
        for rx, ry in rock_positions:
            pygame.draw.circle(screen, rock_color, (int(rx), int(ry)), 36)
            pygame.draw.circle(screen, rock_highlight, (int(rx - 12), int(ry - 14)), 10)
    else:
        field_width = screen.get_width()
        field_height = screen.get_height()
        grass_base = (58, 145, 62)
        grass_light = (76, 175, 80)
        pad = 60
        bg_rect = pygame.Rect(-pad, -pad, field_width + pad * 2, field_height + pad * 2)
        pygame.draw.rect(screen, grass_base, bg_rect)
        stripe_h = 12
        step = 44
        for yy in range(-pad, field_height + pad, step):
            stripe = pygame.Rect(-pad, yy, field_width + pad * 2, stripe_h)
            pygame.draw.rect(screen, grass_light, stripe)

        rock_color = (120, 120, 120)
        rock_shadow = (80, 80, 80)
        rock_positions = [
            (field_width * 0.18, field_height * 0.62),
            (field_width * 0.75, field_height * 0.80),
            (field_width * 0.40, field_height * 0.40),
            (field_width * 0.60, field_height * 0.25),
        ]
        for rx, ry in rock_positions:
            center = pygame.Vector2(rx, ry)
            pygame.draw.circle(screen, rock_shadow, (int(center.x + 8), int(center.y + 8)), 22)
            pygame.draw.circle(screen, rock_color, (int(center.x), int(center.y)), 22)
            pygame.draw.circle(screen, (180, 180, 180), (int(center.x - 6), int(center.y - 8)), 8)

        flower_centers = [
            (field_width * 0.13, field_height * 0.63),
            (field_width * 0.60, field_height * 0.60),
            (field_width * 0.21, field_height * 0.66),
            (field_width * 0.80, field_height * 0.30),
        ]
        for fx, fy in flower_centers:
            center = pygame.Vector2(fx, fy)
            for angle in range(0, 360, 72):
                offset = pygame.Vector2(0, 10).rotate(angle)
                pygame.draw.circle(screen, (255, 255, 255), (int(center.x + offset.x), int(center.y + offset.y)), 6)
            pygame.draw.circle(screen, (255, 220, 80), (int(center.x), int(center.y)), 6)

        table_color = (150, 100, 40)
        table_outline = (90, 60, 20)
        leg_color = (120, 80, 35)
        table_w, table_h = 160, 60
        leg_w, leg_h = 10, 36
        t_center = pygame.Vector2(field_width * 0.12, field_height * 0.60)
        t_rect = pygame.Rect(int(t_center.x - table_w / 2), int(t_center.y - table_h / 2), table_w, table_h)
        pygame.draw.rect(screen, table_color, t_rect)
        pygame.draw.rect(screen, table_outline, t_rect, 2)
        legs = [
            pygame.Rect(t_rect.left + 12, t_rect.bottom, leg_w, leg_h),
            pygame.Rect(t_rect.right - 12 - leg_w, t_rect.bottom, leg_w, leg_h),
            pygame.Rect(t_rect.left + 12, t_rect.bottom + leg_h + 2, leg_w, 2),
            pygame.Rect(t_rect.right - 12 - leg_w, t_rect.bottom + leg_h + 2, leg_w, 2),
        ]
        for lr in legs:
            pygame.draw.rect(screen, leg_color, lr)

        # Shopkeeper behind the table
        npc_rect = get_shopkeeper_rect(screen)
        pygame.draw.rect(screen, (90, 60, 20), npc_rect)
        pygame.draw.rect(screen, (70, 40, 10), npc_rect, 2)
        head_center = (npc_rect.centerx, npc_rect.top + 12)
        pygame.draw.circle(screen, (240, 210, 180), head_center, 10)
        prompt = state.font.render('Click on me to talk', True, (255, 255, 200))
        screen.blit(prompt, (npc_rect.centerx - prompt.get_width() // 2, npc_rect.top - 26))

        icon_x = t_rect.centerx - 16
        icon_y = t_rect.centery - 16
        if not state.leather_armor_bought:
            pygame.draw.rect(screen, (139, 69, 19), (icon_x, icon_y, 32, 32))
        label = (
            f"Leather Armor - {settings.SPEED_POTION_COST} coins"
            if not state.leather_armor_bought
            else "SOLD OUT"
        )
        tip = "Press E to buy" if not state.leather_armor_bought else "You own it!"
        label_surf = state.font.render(label, True, (255, 255, 255))
        tip_surf = state.font.render(tip, True, (220, 220, 220))
        screen.blit(label_surf, (t_rect.centerx - label_surf.get_width() // 2, t_rect.top - 22))
        screen.blit(tip_surf, (t_rect.centerx - tip_surf.get_width() // 2, t_rect.bottom + 8))

    draw_player_health_bar_topleft(screen, player.health, player.max_health, 10, 10)
    draw_potion_icon(screen, 100, 6, enabled="heal" if player.potion_count > 0 else None)
    draw_coin_icon(screen, 124, 6, enabled=True)
    coins_text = state.font.render(f"x {state.coin_count}", True, (255, 255, 255))
    screen.blit(coins_text, (144, 6))

    if player.health > 0:
        move_speed = player.speed if player.health > 0 else 0
        leg_swing = 0
        if move_speed > 0 and (keys[pygame.K_w] or keys[pygame.K_a] or keys[pygame.K_s] or keys[pygame.K_d]):
            leg_swing = int(18 * math.sin(pygame.time.get_ticks() * 0.008))
        p = player.pos
        leg_len = settings.PLAYER_RADIUS + 18
        pygame.draw.line(screen, (60, 0, 0), (int(p.x - 16), int(p.y + settings.PLAYER_RADIUS)), (int(p.x - 16 + leg_swing), int(p.y + leg_len)), 8)
        pygame.draw.line(screen, (60, 0, 0), (int(p.x + 16), int(p.y + settings.PLAYER_RADIUS)), (int(p.x + 16 - leg_swing), int(p.y + leg_len)), 8)
        body_color = (200, 80, 80) if player.is_dodging else "red"
        pygame.draw.circle(screen, body_color, player.pos, settings.PLAYER_RADIUS)
        if player.armor_equipped:
            # Simple chest plate overlay
            pygame.draw.circle(screen, (150, 90, 40), player.pos, settings.PLAYER_RADIUS - 6, 6)
        if player.is_blocking:
            pts = sword_polygon_points(
                player.pos,
                player.facing,
                settings.SHIELD_DISTANCE,
                settings.SHIELD_LENGTH,
                settings.SHIELD_WIDTH,
            )
            pygame.draw.polygon(screen, (120, 170, 255), pts)

    for coin in state.coin_pickups:
        cpos = coin["pos"]
        pygame.draw.circle(screen, (255, 215, 0), (int(cpos.x), int(cpos.y)), 10)
        pygame.draw.circle(screen, (90, 70, 0), (int(cpos.x), int(cpos.y)), 10, 2)

    if state.door_revealed:
        door = get_door_rect(state.level_index, state.screen)
        if state.level_index == 1:
            pygame.draw.rect(screen, settings.FIRST_ROOM_DOOR_COLOR, door)
            pygame.draw.rect(screen, settings.FIRST_ROOM_DOOR_OUTLINE, door, 6)
        else:
            pygame.draw.rect(screen, (90, 60, 20), door)
            pygame.draw.rect(screen, (180, 140, 60), door, 3)

    for pig in state.pigs:
        if pig.health <= 0:
            continue
        pig_leg_swing = int(16 * math.sin(pygame.time.get_ticks() * 0.008 + pig.pos.x))
        pp = pig.pos
        pig_leg_len = settings.PIG_RADIUS + 14
        pygame.draw.line(screen, (0, 60, 0), (int(pp.x - 14), int(pp.y + settings.PIG_RADIUS)), (int(pp.x - 14 + pig_leg_swing), int(pp.y + pig_leg_len)), 7)
        pygame.draw.line(screen, (0, 60, 0), (int(pp.x + 14), int(pp.y + settings.PIG_RADIUS)), (int(pp.x + 14 - pig_leg_swing), int(pp.y + pig_leg_len)), 7)
        pygame.draw.circle(screen, "green", pig.pos, settings.PIG_RADIUS)

        pig_draw_dir = (
            get_swing_dir(pig.swing_base_dir, pig.swing_timer, settings.PIG_SWING_TIME, pig.facing)
            if pig.swing_timer > 0
            else pig.facing
        )
        es_pts = sword_polygon_points(
            pig.pos,
            pig_draw_dir,
            settings.PIG_SWING_DISTANCE,
            settings.SWORD_LENGTH,
            settings.SWORD_WIDTH,
        )
        if pig.swing_timer > 0:
            pygame.draw.polygon(screen, (180, 255, 180), es_pts)
        else:
            pygame.draw.polygon(screen, (200, 200, 200), es_pts, 1)

        draw_health_bar_above(screen, pig.pos, pig.health, settings.PIG_MAX_HEALTH)

    if player.health > 0:
        player_draw_dir = (
            get_swing_dir(player.swing_base_dir, player.swing_timer, settings.PLAYER_SWING_TIME, player.facing)
            if player.swing_timer > 0
            else player.facing
        )
        ps_pts = sword_polygon_points(
            player.pos,
            player_draw_dir,
            settings.PLAYER_SWING_DISTANCE,
            settings.SWORD_LENGTH,
            settings.SWORD_WIDTH,
        )
        if player.swing_timer > 0:
            pygame.draw.polygon(screen, (255, 220, 180), ps_pts)
        else:
            pygame.draw.polygon(screen, (200, 200, 200), ps_pts, 1)

    if state.blood_splats:
        blood_color = (160, 0, 0)
        for s in state.blood_splats:
            for pos, rad in s["points"]:
                pygame.draw.circle(screen, blood_color, (int(pos.x), int(pos.y)), int(rad), 1)

    pigs_alive = sum(1 for p in state.pigs if p.health > 0)
    hud2 = state.font.render(f"Pigs alive: {pigs_alive}", True, (255, 255, 255))
    hud3 = state.font.render(f"LMB = swing sword ({settings.PLAYER_DAMAGE} dmg)", True, (255, 255, 255))
    screen.blit(hud2, (10, 36))
    screen.blit(hud3, (10, 62))

    if state.leather_armor_bought:
        armor_text = state.font.render("Leather Armor: 5% damage blocked", True, (200, 180, 120))
        screen.blit(armor_text, (10, 110))
    if state.has_map:
        map_text = state.font.render("Map: press M", True, (180, 220, 255))
        screen.blit(map_text, (10, 158))

    if state.inventory_open:
        inv_font = pygame.font.SysFont(None, 32)
        inv_bg = (30, 30, 60)
        slot_w, slot_h = 60, 60
        margin = 10
        inv_x = screen.get_width() // 2 - (slot_w * 5 + margin * 4) // 2
        inv_y = 120
        for i in range(settings.INVENTORY_SLOTS):
            x = inv_x + i * (slot_w + margin)
            y = inv_y
            pygame.draw.rect(screen, inv_bg, (x, y, slot_w, slot_h))
            pygame.draw.rect(screen, (200, 200, 255), (x, y, slot_w, slot_h), 2)
            item = state.inventory[i]
            if item == "Speed Potion":
                draw_potion_icon(screen, x + slot_w // 2 - 7, y + slot_h // 2 - 14, enabled="speed")
                label = inv_font.render("Speed", True, (120, 180, 255))
                screen.blit(label, (x + 4, y + slot_h - 24))
            elif item:
                label = inv_font.render(item, True, (255, 255, 255))
                screen.blit(label, (x + 4, y + slot_h // 2 - 8))
            num = inv_font.render(str(i + 1), True, (180, 180, 180))
            screen.blit(num, (x + slot_w - 18, y + slot_h - 28))

    if player.shield_blocks_left == 0:
        warn = state.font.render("shield broken!", True, (255, 120, 120))
        screen.blit(warn, (10, 88))
    elif 0 < player.shield_blocks_left <= 2:
        warn = state.font.render("shield damaged!", True, (255, 235, 59))
        screen.blit(warn, (10, 88))
    if player.is_dodging:
        dodge_text = state.font.render("Dodging!", True, (120, 255, 120))
        screen.blit(dodge_text, (10, 134))
    elif player.dodge_cooldown > 0:
        cd_text = state.font.render(f"Dodge CD: {player.dodge_cooldown:.1f}s", True, (180, 180, 180))
        screen.blit(cd_text, (10, 134))
    if state.dialogue_lines:
        draw_dialogue(state)
    if state.map_open and state.has_map:
        full_rect = pygame.Rect(0, 0, screen.get_width(), screen.get_height())
        pygame.draw.rect(screen, (220, 240, 255), full_rect)
        pygame.draw.rect(screen, (100, 130, 160), full_rect, 6)
        return


def run():
    pygame.init()
    screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
    state = create_game_state(screen)
    reset_round(state)

    while state.running:
        events = pygame.event.get()
        if state.game_over:
            handle_death_screen(state, events)
            continue

        handle_events(state, events)
        update_game(state)
        draw_game(state)
        pygame.display.flip()
        state.dt = state.clock.tick(settings.TARGET_FPS) / 1000

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run()
