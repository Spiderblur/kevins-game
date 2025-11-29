import pygame
import sys
import math
import random

# pygame setup
pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
running = True
dt = 0
game_over = False

# (Sound removed)

# --- Player & Pig setup ---
START_PLAYER_POS = pygame.Vector2(screen.get_width() / 2, screen.get_height() / 2)
START_PIG_POS = pygame.Vector2(screen.get_width() / 4, screen.get_height() / 2)
player_pos = START_PLAYER_POS.copy()
PLAYER_RADIUS = 40
PIG_RADIUS = 40

# Health
PLAYER_MAX_HEALTH = 100
PIG_MAX_HEALTH = 100
player_health = PLAYER_MAX_HEALTH

# Movement / AI
PLAYER_BASE_SPEED = 300
player_speed = PLAYER_BASE_SPEED
pig_speed = 150
chase_range = 500

# Facing (where the sword appears). Start facing right.
player_facing = pygame.Vector2(1, 0)

# Sword (shared settings)
SWORD_LENGTH = 60
SWORD_WIDTH = 14
# Damage
PLAYER_DAMAGE = 20
PIG_DAMAGE = 5  # each pig deals 5 damage
PLAYER_SWING_TIME = 0.18  # seconds sword is "active"
PIG_SWING_TIME = 0.18
PLAYER_COOLDOWN = 0.5  # time before next swing
PIG_COOLDOWN = 0.5
PLAYER_SWING_DISTANCE = PLAYER_RADIUS + 8
PIG_SWING_DISTANCE = PIG_RADIUS + 8
SWING_ARC_DEG = 80  # total arc angle for sword swing animation

# Knockback (how hard and how long you slide back when hit)
KNOCKBACK_SPEED = 420  # pixels per second pushed back
KNOCKBACK_DURATION = 0.18  # seconds of knockback

# Screen shake (camera wiggle) when someone gets hit
SHAKE_INTENSITY = 8  # how strong the shake (pixels)
SHAKE_DURATION = 0.15  # how long the shake lasts (seconds)

# Swing state
player_swing_timer = 0.0
player_cooldown = 0.0
player_swing_base_dir = pygame.Vector2(1, 0)  # captured at swing start for animation

# Shield
SHIELD_LENGTH = 36  # how far the shield extends forward
SHIELD_WIDTH = 36  # how wide/thick the shield looks
SHIELD_DISTANCE = PLAYER_RADIUS - 6  # how far from player center
is_blocking = False
SHIELD_MAX_BLOCKS = 5
shield_blocks_left = SHIELD_MAX_BLOCKS

# Potion (top-left, press Q to heal)
POTION_HEAL = 30
potion_count = 1  # one small potion
is_drinking_potion = False
potion_timer = 0.0
COIN_VALUE = 5
COIN_PICKUP_RADIUS = 50
coin_pickups = []  # list of dicts: { 'pos': Vector2, 'value': int }
coin_count = 0
pig_coin_dropped = False  # legacy, not used with multiple pigs
SPEED_POTION_COST = 10
SPEED_BOOST_MULT = 1.3
leather_armor_bought = False

# Inventory system: 10 slots, empty string means empty slot
inventory = ["" for _ in range(10)]
inventory_open = False

font = pygame.font.SysFont(None, 26)

# Knockback state (timers and direction vectors)
player_knockback_timer = 0.0
player_knockback_vec = pygame.Vector2(0, 0)

# Multiple pigs: each pig has its own state in this list
pigs = (
    []
)  # list of dicts: {pos, health, facing, swing_timer, cooldown, knockback_timer, knockback_vec, coin_dropped}


def make_pig(pos):
    return {
        "pos": pygame.Vector2(pos),
        "health": PIG_MAX_HEALTH,
        "facing": pygame.Vector2(1, 0),
        "swing_timer": 0.0,
        "cooldown": 0.0,
        "knockback_timer": 0.0,
        "knockback_vec": pygame.Vector2(0, 0),
        "coin_dropped": False,
        "swing_base_dir": pygame.Vector2(1, 0),
    }


def spawn_pigs(n):
    global level_index
    pigs.clear()
    # Spread pigs vertically around center
    spacing = 80
    center_y = screen.get_height() / 2
    start_y = center_y - (spacing * (n - 1) / 2)
    # Base X position; in room 2, shift them right a bit
    base_x = START_PIG_POS.x
    if level_index == 2:
        base_x += 220  # move further to the right in the second room
    for i in range(n):
        y = start_y + i * spacing
        pos = pygame.Vector2(base_x, y)
        pigs.append(make_pig(pos))


# Hit VFX: screen shake timer and simple blood splatter outlines
shake_timer = 0.0
blood_splats = []  # list of { 'points': [(Vector2, radius), ...], 'timer': float }


def spawn_blood_splatter(center, count_min=8, count_max=14, ring_min=8, ring_max=26):
    """Add a quick ring of small outline circles around the hit point.

    center: Vector2 world position of the hit.
    """
    count = random.randint(count_min, count_max)
    pts = []
    for _ in range(count):
        angle_deg = random.uniform(0, 360)
        dir_vec = pygame.Vector2(1, 0).rotate(angle_deg)
        dist = random.uniform(ring_min, ring_max)
        pos = pygame.Vector2(center) + dir_vec * dist
        radius = random.uniform(2, 5)
        pts.append((pos, radius))
    blood_splats.append({"points": pts, "timer": 0.6})


# Door/level state
DOOR_WIDTH = 40
DOOR_HEIGHT = 120
DOOR_MARGIN = 10  # space from the right edge

# Make the first room door bigger and more visible
FIRST_ROOM_DOOR_WIDTH = 120
FIRST_ROOM_DOOR_HEIGHT = 180
FIRST_ROOM_DOOR_COLOR = (255, 255, 80)
FIRST_ROOM_DOOR_OUTLINE = (255, 255, 255)
door_revealed = False
level_index = 1


def get_door_rect():
    if level_index == 1:
        x = screen.get_width() - DOOR_MARGIN - FIRST_ROOM_DOOR_WIDTH
        y = (screen.get_height() - FIRST_ROOM_DOOR_HEIGHT) // 2
        return pygame.Rect(x, y, FIRST_ROOM_DOOR_WIDTH, FIRST_ROOM_DOOR_HEIGHT)
    else:
        x = screen.get_width() - DOOR_MARGIN - DOOR_WIDTH
        y = (screen.get_height() - DOOR_HEIGHT) // 2
        return pygame.Rect(x, y, DOOR_WIDTH, DOOR_HEIGHT)


def get_room3_table_rect(cam_offset=pygame.Vector2(0, 0)):
    """Return the table rect in room 3 (world space), optionally offset for camera."""
    table_w, table_h = 160, 60
    t_center = pygame.Vector2(screen.get_width() * 0.68, screen.get_height() * 0.60)
    return pygame.Rect(
        int(t_center.x - table_w / 2 + cam_offset.x),
        int(t_center.y - table_h / 2 + cam_offset.y),
        table_w,
        table_h,
    )


# Spawn initial level pigs
spawn_pigs(1)


def draw_player_health_bar_topleft(current, maximum, x=10, y=10):
    """Draw a health bar at the top-left like the pig's (gray bg + red fill)."""
    bar_width = 80
    bar_height = 10
    pygame.draw.rect(screen, (100, 100, 100), (x, y, bar_width, bar_height))
    ratio = max(0, current) / maximum if maximum > 0 else 0
    pygame.draw.rect(screen, (255, 0, 0), (x, y, int(bar_width * ratio), bar_height))


def draw_health_bar_above(center_pos, current, maximum):
    """Draws a gray background bar and a red health bar above the pig."""
    bar_width = 80
    bar_height = 10
    x = center_pos.x - bar_width // 2
    y = center_pos.y - (PIG_RADIUS + 28)
    pygame.draw.rect(screen, (100, 100, 100), (x, y, bar_width, bar_height))
    ratio = max(0, current) / maximum
    pygame.draw.rect(screen, (255, 0, 0), (x, y, int(bar_width * ratio), bar_height))


def draw_coin_icon(x, y, enabled=True):
    """Draw a small coin icon at the given top-left (x,y)."""
    outline = (90, 70, 0)
    fill = (255, 215, 0) if enabled else (140, 140, 140)
    center = (x + 8, y + 8)
    pygame.draw.circle(screen, fill, center, 8)
    pygame.draw.circle(screen, outline, center, 8, 1)


def draw_potion_icon(x, y, enabled=True):
    """Draw a tiny potion bottle icon at (x,y)."""
    # Colors
    glass = (200, 230, 255) if enabled else (120, 120, 120)
    # Draw red for healing, blue for speed
    if enabled == "heal":
        liquid = (220, 50, 50)
    elif enabled == "speed":
        liquid = (50, 120, 255)
    else:
        liquid = (90, 90, 90)
    outline = (40, 40, 40)

    # Bottle body
    body_rect = pygame.Rect(x, y + 6, 14, 14)
    pygame.draw.rect(screen, glass, body_rect)
    # Liquid fill (lower half)
    liquid_rect = pygame.Rect(x + 2, y + 12, 10, 6)
    pygame.draw.rect(screen, liquid, liquid_rect)
    # Neck/cap
    neck_rect = pygame.Rect(x + 4, y + 2, 6, 4)
    cap_rect = pygame.Rect(x + 3, y, 8, 2)
    pygame.draw.rect(screen, glass, neck_rect)
    pygame.draw.rect(screen, outline, cap_rect)
    # Outline
    pygame.draw.rect(screen, outline, body_rect, 1)
    pygame.draw.rect(screen, outline, neck_rect, 1)


def circle_rect(center, radius):
    """Return a Rect that bounds a circle (useful for collision)."""
    return pygame.Rect(center.x - radius, center.y - radius, radius * 2, radius * 2)


def get_sword_segment(center, facing_vec, extend_distance, length):
    """Return the start and end points of the sword along facing direction."""
    f = pygame.Vector2(facing_vec)
    if f.length_squared() == 0:
        return center, center
    f = f.normalize()
    start = center + f * extend_distance
    end = start + f * length
    return start, end


def sword_polygon_points(center, facing_vec, extend_distance, length, width):
    """Return 4 points of a rectangle representing the sword, rotated to face facing_vec."""
    start, end = get_sword_segment(center, facing_vec, extend_distance, length)
    f = end - start
    if f.length_squared() == 0:
        return [start, start, start, start]
    f = f.normalize()
    # Perpendicular vector for thickness
    n = pygame.Vector2(-f.y, f.x) * (width / 2)
    p1 = start + n
    p2 = start - n
    p3 = end - n
    p4 = end + n
    return [p1, p2, p3, p4]


def get_swing_dir(base_dir, swing_timer, total_time, fallback_dir):
    """Compute a rotated direction vector for a sword swing animation.

    Sweeps from -SWING_ARC_DEG/2 to +SWING_ARC_DEG/2 across the swing duration.
    """
    if swing_timer <= 0 or total_time <= 0:
        return fallback_dir
    phase = 1.0 - max(0.0, min(1.0, swing_timer / total_time))  # 0..1
    start_angle = -SWING_ARC_DEG / 2
    angle = start_angle + SWING_ARC_DEG * phase
    b = pygame.Vector2(base_dir)
    if b.length_squared() == 0:
        b = pygame.Vector2(fallback_dir)
    return b.rotate(angle)


def point_segment_distance(p, a, b):
    """Distance from point p to line segment a-b."""
    ap = p - a
    ab = b - a
    ab_len2 = ab.length_squared()
    if ab_len2 == 0:
        return ap.length()
    t = max(0.0, min(1.0, ap.dot(ab) / ab_len2))
    closest = a + ab * t
    return (p - closest).length()


def deal_damage_if_hit(
    attacker_center,
    attacker_facing,
    target_center,
    target_radius,
    swing_timer,
    swing_time,
    damage,
):
    """
    If the attacker's sword is currently active (swing_timer > 0),
    check overlap with the target's bounding rect. Return damage_to_apply (0 or damage).
    """
    if swing_timer <= 0:
        return 0
    extend = (
        PLAYER_SWING_DISTANCE if attacker_center is player_pos else PIG_SWING_DISTANCE
    )
    start, end = get_sword_segment(
        attacker_center, attacker_facing, extend, SWORD_LENGTH
    )
    dist = point_segment_distance(target_center, start, end)
    return damage if dist <= (target_radius + SWORD_WIDTH / 2) else 0


def reset_round():
    """Reset positions, health, and combat state to fight again."""
    global player_health, player_pos, player_swing_timer, player_cooldown
    global is_blocking, shield_blocks_left, game_over, coin_pickups, potion_count
    global player_knockback_timer, player_knockback_vec
    global door_revealed, pigs
    global shake_timer

    player_health = PLAYER_MAX_HEALTH
    # For room 3, spawn at the start of the path
    if level_index == 3:
        field_height = 2400
        player_pos.update(PLAYER_RADIUS + 20, field_height / 2)
    else:
        player_pos.update(START_PLAYER_POS)
    player_swing_timer = 0.0
    player_cooldown = 0.0
    is_blocking = False
    shield_blocks_left = SHIELD_MAX_BLOCKS
    potion_count = 1  # refill potion on new screen/round
    try:
        coin_pickups.clear()
    except NameError:
        pass
    # Reset knockback
    player_knockback_timer = 0.0
    player_knockback_vec.update(0, 0)
    # Reset hit effects
    shake_timer = 0.0
    try:
        blood_splats.clear()
    except NameError:
        pass
    game_over = False
    door_revealed = False

    # Spawn pigs for this level
    # Room 1: 1 pig, Room 2: 2 pigs, Room 3+: 0 pigs (final room)
    if level_index <= 1:
        n = 1
    elif level_index == 2:
        n = 2
    else:
        n = 0
    spawn_pigs(n)


while running:
    # --- Events ---
    events = pygame.event.get()
    # Death screen menu
    if game_over:
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_c, pygame.K_RETURN, pygame.K_SPACE):
                    reset_round()
                elif event.key in (pygame.K_ESCAPE, pygame.K_e):
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Click handling after we compute rects below
                pass

        # Draw death screen
        screen.fill((0, 0, 0))
        title_font = pygame.font.SysFont(None, 120)
        menu_font = pygame.font.SysFont(None, 48)
        death_text = title_font.render("YOU DIED!", True, (255, 0, 0))
        death_rect = death_text.get_rect(
            center=(screen.get_width() / 2, screen.get_height() / 2 - 40)
        )
        cont_text = menu_font.render("Continue", True, (255, 255, 255))
        exit_text = menu_font.render("Exit", True, (255, 255, 255))
        cont_rect = cont_text.get_rect(
            center=(screen.get_width() / 2, screen.get_height() / 2 + 20)
        )
        exit_rect = exit_text.get_rect(
            center=(screen.get_width() / 2, screen.get_height() / 2 + 70)
        )

        # Handle mouse click on buttons
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if cont_rect.collidepoint(event.pos):
                    reset_round()
                elif exit_rect.collidepoint(event.pos):
                    running = False

        screen.blit(death_text, death_rect)
        screen.blit(cont_text, cont_rect)
        screen.blit(exit_text, exit_rect)
        pygame.display.flip()
        dt = clock.tick(60) / 1000
        continue

    for event in events:
        if event.type == pygame.QUIT:
            running = False
        # Left click = attack (disabled while blocking or drinking potion)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if (
                player_health > 0
                and player_cooldown <= 0
                and player_swing_timer <= 0
                and not is_blocking
                and not is_drinking_potion
            ):
                player_swing_timer = PLAYER_SWING_TIME
                player_cooldown = PLAYER_COOLDOWN
                # Capture base direction for the swing animation
                if player_facing.length_squared() > 0:
                    player_swing_base_dir = player_facing.normalize()
                else:
                    player_swing_base_dir = pygame.Vector2(1, 0)
        # Right click = hold to block
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if player_health > 0 and shield_blocks_left > 0:
                is_blocking = True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            is_blocking = False
        # Use potion with Q (takes 1 second to drink)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
            if (
                potion_count > 0
                and player_health > 0
                and player_health < PLAYER_MAX_HEALTH
                and not is_drinking_potion
            ):
                is_drinking_potion = True
                potion_timer = 1.0
        # Buy speed potion in room 3 by pressing E near the table
        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            if level_index >= 3 and not leather_armor_bought:
                t_rect = get_room3_table_rect(pygame.Vector2(0, 0))
                near_rect = t_rect.inflate(PLAYER_RADIUS * 2, PLAYER_RADIUS * 2)
                if near_rect.collidepoint(player_pos.x, player_pos.y):
                    if coin_count >= SPEED_POTION_COST:
                        coin_count -= SPEED_POTION_COST
                        leather_armor_bought = True
        # Use speed potion by left-clicking it in inventory
        if inventory_open and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_x, mouse_y = event.pos
            slot_w, slot_h = 60, 60
            margin = 10
            inv_x = screen.get_width() // 2 - (slot_w * 5 + margin * 4) // 2
            inv_y = 120
            for i in range(10):
                x = inv_x + i * (slot_w + margin)
                y = inv_y
                rect = pygame.Rect(x, y, slot_w, slot_h)
                if rect.collidepoint(mouse_x, mouse_y) and inventory[i] == "Speed Potion":
                    # Drink the speed potion: 50% speed boost
                    player_speed = int(PLAYER_BASE_SPEED * 1.5)
                    inventory[i] = ""
                    break
        # Toggle inventory with T
        if event.type == pygame.KEYDOWN and event.key == pygame.K_t:
            inventory_open = not inventory_open

    # --- Logic ---
    keys = pygame.key.get_pressed()
    if player_health > 0:
        move = pygame.Vector2(0, 0)
        if keys[pygame.K_w]:
            move.y -= 1
        if keys[pygame.K_s]:
            move.y += 1
        if keys[pygame.K_a]:
            move.x -= 1
        if keys[pygame.K_d]:
            move.x += 1
        if move.length_squared() > 0:
            move = move.normalize()
            player_pos += move * player_speed * dt

        # Apply knockback movement if recently hit
        if "player_knockback_timer" in globals() and player_knockback_timer > 0:
            player_pos += player_knockback_vec * (KNOCKBACK_SPEED * dt)
            player_knockback_timer -= dt

        # Aim sword toward the mouse cursor
        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        to_mouse = mouse_pos - player_pos
        if to_mouse.length_squared() > 0:
            player_facing = to_mouse.normalize()

    # Pig AI and actions for each alive pig
    for pig in pigs:
        if pig["health"] <= 0:
            continue
        to_player = player_pos - pig["pos"]
        dist = to_player.length()
        if dist > 0:
            pig["facing"] = to_player / dist
        if dist < chase_range and dist > 0:
            pig["pos"] += pig["facing"] * pig_speed * dt

            # Pig auto-swings if in striking distance and not on cooldown
            if dist < (PIG_RADIUS + PLAYER_RADIUS + SWORD_LENGTH * 0.6):
                if pig["cooldown"] <= 0 and pig["swing_timer"] <= 0:
                    pig["swing_timer"] = PIG_SWING_TIME
                    pig["cooldown"] = PIG_COOLDOWN
                    pig["swing_base_dir"] = pig["facing"].copy()

        # Apply knockback movement to pig if recently hit
        if pig["knockback_timer"] > 0:
            pig["pos"] += pig["knockback_vec"] * (KNOCKBACK_SPEED * dt)
            pig["knockback_timer"] -= dt

    # Timers
    if player_swing_timer > 0:
        player_swing_timer -= dt
    if player_cooldown > 0:
        player_cooldown -= dt
    # Pigs' swing and cooldown timers
    for pig in pigs:
        if pig["swing_timer"] > 0:
            pig["swing_timer"] -= dt
            if pig["swing_timer"] < 0:
                pig["swing_timer"] = 0
        if pig["cooldown"] > 0:
            pig["cooldown"] -= dt
            if pig["cooldown"] < 0:
                pig["cooldown"] = 0
    # Potion drinking timer
    if is_drinking_potion:
        potion_timer -= dt
        if potion_timer <= 0:
            player_health = min(PLAYER_MAX_HEALTH, player_health + POTION_HEAL)
            potion_count -= 1
            is_drinking_potion = False

    # Update knockback timers handled above; update screen shake timer
    if shake_timer > 0:
        shake_timer -= dt
        if shake_timer < 0:
            shake_timer = 0

    # Update blood splats timers and cleanup
    if blood_splats:
        keep = []
        for s in blood_splats:
            s["timer"] -= dt
            if s["timer"] > 0:
                keep.append(s)
        blood_splats = keep

    # --- Combat: apply damage if a sword is currently active ---
    # Player hitting Pigs (only if player is alive)
    if player_health > 0:
        for pig in pigs:
            if pig["health"] <= 0:
                continue
            # Animated attack direction during swing
            player_attack_dir = (
                get_swing_dir(
                    player_swing_base_dir,
                    player_swing_timer,
                    PLAYER_SWING_TIME,
                    player_facing,
                )
                if player_swing_timer > 0
                else player_facing
            )
            dmg_to_pig = deal_damage_if_hit(
                player_pos,
                player_attack_dir,
                pig["pos"],
                PIG_RADIUS,
                player_swing_timer,
                PLAYER_SWING_TIME,
                PLAYER_DAMAGE,
            )
            if dmg_to_pig:
                pig["health"] = max(0, pig["health"] - dmg_to_pig)
                # Prevent multiple hits during one swing: end the swing timer now
                player_swing_timer = 0
                # Apply knockback to pig: push away from player
                dir_vec = pig["pos"] - player_pos
                if dir_vec.length_squared() > 0:
                    pig["knockback_vec"] = dir_vec.normalize()
                    pig["knockback_timer"] = KNOCKBACK_DURATION
                # Hit effects
                shake_timer = max(shake_timer, SHAKE_DURATION)
                spawn_blood_splatter(pig["pos"])
                # Drop a coin once when the pig dies
                if pig["health"] == 0 and not pig["coin_dropped"]:
                    coin_pickups.append({"pos": pig["pos"].copy(), "value": COIN_VALUE})
                    pig["coin_dropped"] = True

        # If all pigs are dead, reveal the door (only before final room)
        if level_index < 3:
            if pigs and not door_revealed and all(p["health"] <= 0 for p in pigs):
                door_revealed = True
        else:
            door_revealed = False

    # Pigs hitting Player
    if player_health > 0:
        for pig in pigs:
            if pig["health"] <= 0:
                continue
            pig_attack_dir = (
                get_swing_dir(
                    pig["swing_base_dir"],
                    pig["swing_timer"],
                    PIG_SWING_TIME,
                    pig["facing"],
                )
                if pig["swing_timer"] > 0
                else pig["facing"]
            )
            dmg_to_player = deal_damage_if_hit(
                pig["pos"],
                pig_attack_dir,
                player_pos,
                PLAYER_RADIUS,
                pig["swing_timer"],
                PIG_SWING_TIME,
                PIG_DAMAGE,
            )
            if dmg_to_player:
                if is_blocking:
                    # Block the attack: no damage, consume durability, cancel this pig's swing
                    pig["swing_timer"] = 0
                    if shield_blocks_left > 0:
                        shield_blocks_left -= 1
                    if shield_blocks_left <= 0:
                        is_blocking = False  # shield breaks
                else:
                    # Apply leather armor reduction if owned
                    if leather_armor_bought:
                        dmg_to_player = int(dmg_to_player * 0.95)
                    player_health = max(0, player_health - dmg_to_player)
                    pig["swing_timer"] = 0
                    # Apply knockback to player: push away from this pig
                    dir_vec = player_pos - pig["pos"]
                    if dir_vec.length_squared() > 0:
                        player_knockback_vec = dir_vec.normalize()
                        player_knockback_timer = KNOCKBACK_DURATION
                    # Hit effects
                    shake_timer = max(shake_timer, SHAKE_DURATION)
                    spawn_blood_splatter(player_pos)
                    if player_health == 0:
                        is_blocking = False
                        game_over = True

    # Auto-pickup coins when close
    if coin_pickups and player_health > 0:
        remaining = []
        for coin in coin_pickups:
            if (player_pos - coin["pos"]).length() <= COIN_PICKUP_RADIUS:
                coin_count += coin["value"]
            else:
                remaining.append(coin)
        coin_pickups = remaining

    # Enter door to go to a new screen
    if door_revealed and player_health > 0:
        door = get_door_rect()
        # Check overlap of player's circle with door rectangle (simple AABB vs circle approximation)
        # We'll consider entering when the player's center is inside the rect inflated by radius
        enter_rect = door.inflate(PLAYER_RADIUS * 2, PLAYER_RADIUS * 2)
        if enter_rect.collidepoint(player_pos.x, player_pos.y):
            # Next "screen": keep background, reset enemies/items, move player to left side
            level_index += 1
            reset_round()
            door_revealed = False
            # Place the player near the left edge for the new screen
            player_pos.update(PLAYER_RADIUS + 20, screen.get_height() / 2)


    # --- Drawing ---
    # Only fill purple if not in room 3
    if level_index != 3:
        # Draw a solid gray background for rooms 1 and 2
        bg_gray = (120, 120, 120)
        screen.fill(bg_gray)
        # Add a few rocks for decoration
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
    # Camera logic
    if level_index == 3:
        cam_offset = pygame.Vector2(0, 0)

    # Room 3 background and props (field + table), drawn in world space with camera
    if level_index == 3:
        # Make the field the size of the screen (original size)
        field_width = screen.get_width()
        field_height = screen.get_height()
        grass_base = (58, 145, 62)
        grass_light = (76, 175, 80)
        pad = 60
        # Always cover the whole field, so the player can't see the edge
        bg_rect = pygame.Rect(
            -pad,
            -pad,
            field_width + pad * 2,
            field_height + pad * 2,
        )
        pygame.draw.rect(screen, grass_base, bg_rect)
        # Horizontal light stripes for a mowed-field look
        stripe_h = 12
        step = 44
        y_start = -pad
        y_end = field_height + pad
        for yy in range(y_start, y_end, step):
            stripe = pygame.Rect(
                -pad,
                yy,
                field_width + pad * 2,
                stripe_h,
            )
            pygame.draw.rect(screen, grass_light, stripe)

        # --- Draw rocks ---
        rock_color = (120, 120, 120)
        rock_shadow = (80, 80, 80)
        # Fewer rocks, more spread out
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

        # --- Draw more flowers, spread out ---
        flower_centers = [
            (field_width * 0.13, field_height * 0.63),
            (field_width * 0.60, field_height * 0.60),
            (field_width * 0.21, field_height * 0.66),
            (field_width * 0.80, field_height * 0.30),
        ]
        for fx, fy in flower_centers:
            center = pygame.Vector2(fx, fy)
            # Draw petals
            for angle in range(0, 360, 72):
                offset = pygame.Vector2(0, 10).rotate(angle)
                pygame.draw.circle(screen, (255, 255, 255), (int(center.x + offset.x), int(center.y + offset.y)), 6)
            # Draw center
            pygame.draw.circle(screen, (255, 220, 80), (int(center.x), int(center.y)), 6)

        # --- Draw the table (same as before) ---
        table_color = (150, 100, 40)
        table_outline = (90, 60, 20)
        leg_color = (120, 80, 35)
        table_w, table_h = 160, 60
        leg_w, leg_h = 10, 36
        # Table world center position (same as before)
        t_center = pygame.Vector2(field_width * 0.12, field_height * 0.60)
        t_rect = pygame.Rect(
            int(t_center.x - table_w / 2),
            int(t_center.y - table_h / 2),
            table_w,
            table_h,
        )
        pygame.draw.rect(screen, table_color, t_rect)
        pygame.draw.rect(screen, table_outline, t_rect, 2)
        # Legs at four corners under table
        legs = []
        legs.append(pygame.Rect(t_rect.left + 12, t_rect.bottom, leg_w, leg_h))
        legs.append(pygame.Rect(t_rect.right - 12 - leg_w, t_rect.bottom, leg_w, leg_h))
        legs.append(
            pygame.Rect(t_rect.left + 12, t_rect.bottom + leg_h + 2, leg_w, 2)
        )  # little foot bar (front)
        legs.append(
            pygame.Rect(t_rect.right - 12 - leg_w, t_rect.bottom + leg_h + 2, leg_w, 2)
        )
        for lr in legs:
            pygame.draw.rect(screen, leg_color, lr)

        # Speed potion for sale on the table (cost 50 coins)
        # Leather armor for sale on the table
        icon_x = t_rect.centerx - 16
        icon_y = t_rect.centery - 16
        if not leather_armor_bought:
            # Draw a brown armor icon (simple rectangle)
            pygame.draw.rect(screen, (139, 69, 19), (icon_x, icon_y, 32, 32))
        label = (
            f"Leather Armor - {SPEED_POTION_COST} coins"
            if not leather_armor_bought
            else "SOLD OUT"
        )
        tip = "Press E to buy" if not leather_armor_bought else "You own it!"
        label_surf = font.render(label, True, (255, 255, 255))
        tip_surf = font.render(tip, True, (220, 220, 220))
        screen.blit(
            label_surf, (t_rect.centerx - label_surf.get_width() // 2, t_rect.top - 22)
        )
        screen.blit(
            tip_surf, (t_rect.centerx - tip_surf.get_width() // 2, t_rect.bottom + 8)
        )

    # Player health bar (top-left) styled like the pig's
    draw_player_health_bar_topleft(player_health, PLAYER_MAX_HEALTH, 10, 10)
    # Potion icon next to health bar
    draw_potion_icon(100, 6, enabled="heal" if potion_count > 0 else None)
    # Coin icon and count
    draw_coin_icon(124, 6, enabled=True)
    coins_text = font.render(f"x {coin_count}", True, (255, 255, 255))
    screen.blit(coins_text, (144, 6))

    # Draw player only if alive
    if player_health > 0:
        # Calculate leg animation (swing back and forth as player moves)
        move_speed = player_speed if player_health > 0 else 0
        leg_swing = 0
        if move_speed > 0 and (keys[pygame.K_w] or keys[pygame.K_a] or keys[pygame.K_s] or keys[pygame.K_d]):
            leg_swing = int(18 * math.sin(pygame.time.get_ticks() * 0.008))
        # Draw legs (2 lines)
        p = player_pos
        leg_len = PLAYER_RADIUS + 18
        pygame.draw.line(screen, (60, 0, 0), (int(p.x - 16), int(p.y + PLAYER_RADIUS)), (int(p.x - 16 + leg_swing), int(p.y + leg_len)), 8)
        pygame.draw.line(screen, (60, 0, 0), (int(p.x + 16), int(p.y + PLAYER_RADIUS)), (int(p.x + 16 - leg_swing), int(p.y + leg_len)), 8)
        # Draw body
        pygame.draw.circle(screen, "red", player_pos, PLAYER_RADIUS)
        if is_blocking:
            pts = sword_polygon_points(
                player_pos,
                player_facing,
                SHIELD_DISTANCE,
                SHIELD_LENGTH,
                SHIELD_WIDTH,
            )
            pygame.draw.polygon(screen, (120, 170, 255), pts)

    # Draw dropped coins in the world
    for coin in coin_pickups:
        cpos = coin["pos"]
        pygame.draw.circle(screen, (255, 215, 0), (int(cpos.x), int(cpos.y)), 10)
        pygame.draw.circle(screen, (90, 70, 0), (int(cpos.x), int(cpos.y)), 10, 2)

    # Draw door (world space) when revealed
    if door_revealed:
        door = get_door_rect()
        if level_index == 1:
            pygame.draw.rect(screen, FIRST_ROOM_DOOR_COLOR, door)
            pygame.draw.rect(screen, FIRST_ROOM_DOOR_OUTLINE, door, 6)
        else:
            pygame.draw.rect(screen, (90, 60, 20), door)  # wooden door
            pygame.draw.rect(screen, (180, 140, 60), door, 3)  # outline

    # Draw pigs and their swords
    for pig in pigs:
        if pig["health"] <= 0:
            continue
        # Pig leg animation
        pig_leg_swing = int(16 * math.sin(pygame.time.get_ticks() * 0.008 + pig["pos"].x))
        pp = pig["pos"]
        pig_leg_len = PIG_RADIUS + 14
        pygame.draw.line(screen, (0, 60, 0), (int(pp.x - 14), int(pp.y + PIG_RADIUS)), (int(pp.x - 14 + pig_leg_swing), int(pp.y + pig_leg_len)), 7)
        pygame.draw.line(screen, (0, 60, 0), (int(pp.x + 14), int(pp.y + PIG_RADIUS)), (int(pp.x + 14 - pig_leg_swing), int(pp.y + pig_leg_len)), 7)
        # Pig body
        pygame.draw.circle(screen, "green", pig["pos"], PIG_RADIUS)

        # Pig sword (rotated polygon) with swing animation
        pig_draw_dir = (
            get_swing_dir(
                pig["swing_base_dir"], pig["swing_timer"], PIG_SWING_TIME, pig["facing"]
            )
            if pig["swing_timer"] > 0
            else pig["facing"]
        )
        es_pts = sword_polygon_points(
            pig["pos"],
            pig_draw_dir,
            PIG_SWING_DISTANCE,
            SWORD_LENGTH,
            SWORD_WIDTH,
        )
        if pig["swing_timer"] > 0:
            pygame.draw.polygon(screen, (180, 255, 180), es_pts)
        else:
            pygame.draw.polygon(screen, (200, 200, 200), es_pts, 1)

        # Pig health bar
        draw_health_bar_above(pig["pos"], pig["health"], PIG_MAX_HEALTH)


# Draw player sword (only if alive) as rotated polygon with swing animation

    if player_health > 0:
        player_draw_dir = (
            get_swing_dir(
                player_swing_base_dir,
                player_swing_timer,
                PLAYER_SWING_TIME,
                player_facing,
            )
            if player_swing_timer > 0
            else player_facing
        )
        ps_pts = sword_polygon_points(
            player_pos,
            player_draw_dir,
            PLAYER_SWING_DISTANCE,
            SWORD_LENGTH,
            SWORD_WIDTH,
        )
        if player_swing_timer > 0:
            pygame.draw.polygon(screen, (255, 220, 180), ps_pts)
        else:
            pygame.draw.polygon(screen, (200, 200, 200), ps_pts, 1)

# Draw blood splatters (outlines) in world space

    if blood_splats:
        BLOOD_COLOR = (160, 0, 0)
        for s in blood_splats:
            for pos, rad in s["points"]:
                pygame.draw.circle(
                    screen, BLOOD_COLOR, (int(pos.x), int(pos.y)), int(rad), 1
                )

# HUD text
    pigs_alive = sum(1 for p in pigs if p["health"] > 0)
    hud2 = font.render(f"Pigs alive: {pigs_alive}", True, (255, 255, 255))
    hud3 = font.render(
        f"LMB = swing sword ({PLAYER_DAMAGE} dmg)", True, (255, 255, 255)
    )
    screen.blit(hud2, (10, 36))
    screen.blit(hud3, (10, 62))

    # Show armor status
    if leather_armor_bought:
        armor_text = font.render("Leather Armor: 5% damage blocked", True, (200, 180, 120))
        screen.blit(armor_text, (10, 110))

    # Draw inventory if open
    if inventory_open:
        inv_font = pygame.font.SysFont(None, 32)
        inv_bg = (30, 30, 60)
        slot_w, slot_h = 60, 60
        margin = 10
        inv_x = screen.get_width() // 2 - (slot_w * 5 + margin * 4) // 2
        inv_y = 120
        # Draw 10 slots in a row
        for i in range(10):
            x = inv_x + i * (slot_w + margin)
            y = inv_y
            pygame.draw.rect(screen, inv_bg, (x, y, slot_w, slot_h))
            pygame.draw.rect(screen, (200, 200, 255), (x, y, slot_w, slot_h), 2)
            item = inventory[i]
            if item == "Speed Potion":
                # Draw blue potion icon in slot
                draw_potion_icon(x + slot_w // 2 - 7, y + slot_h // 2 - 14, enabled="speed")
                label = inv_font.render("Speed", True, (120, 180, 255))
                screen.blit(label, (x + 4, y + slot_h - 24))
            elif item:
                label = inv_font.render(item, True, (255, 255, 255))
                screen.blit(label, (x + 4, y + slot_h // 2 - 8))
            # Draw slot number
            num = inv_font.render(str(i+1), True, (180, 180, 180))
            screen.blit(num, (x + slot_w - 18, y + slot_h - 28))

# Show warning when shield is on its last two hits, and 'broken' when at 0
    if shield_blocks_left == 0:
        warn = font.render("shield broken!", True, (255, 120, 120))
        screen.blit(warn, (10, 88))
    elif 0 < shield_blocks_left <= 2:
        warn = font.render("shield damaged!", True, (255, 235, 59))
        screen.blit(warn, (10, 88))

# Flip and tick
    pygame.display.flip()
    dt = clock.tick(60) / 1000

sys.exit()

pygame.quit()
sys.exit()