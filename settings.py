"""Shared game settings and constants."""

# Screen
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
TARGET_FPS = 60
# Levels
FIELD_LEVEL_INDEX = 4

# Radii
PLAYER_RADIUS = 40
PIG_RADIUS = 40

# Health
PLAYER_MAX_HEALTH = 100
PIG_MAX_HEALTH = 100

# Movement / AI
PLAYER_BASE_SPEED = 300
PIG_SPEED = 150
CHASE_RANGE = 500
ALLY_PIG_SPEED = 220
ALLY_PIG_DAMAGE = 8

# Sword
SWORD_LENGTH = 64
SWORD_WIDTH = 14
PLAYER_DAMAGE = 10
PIG_DAMAGE = 5  # each pig deals 5 damage
PLAYER_SWING_TIME = 0.45  # longer active window for a weightier swing
PLAYER_SWING_RECOVER_TIME = 0.18  # time to settle arm/sword back to idle
PIG_SWING_TIME = 0.5  # active swing window (pairs with windup for 1.5s total)
PLAYER_COOLDOWN = 0.5  # time before next swing
PIG_COOLDOWN = 0.0  # no extra delay beyond windup + swing
PIG_WINDUP_TIME = 1.0  # pause before swinging
PLAYER_SWING_DISTANCE = PLAYER_RADIUS + 16
PIG_SWING_DISTANCE = PLAYER_SWING_DISTANCE  # match player reach
SWING_ARC_DEG = 60  # total arc angle for sword swing animation (smaller front swing)
BOW_DAMAGE = 4
BOW_SPEED = 640
BOW_COOLDOWN = 0.45

# Stamina / sprint
STAMINA_MAX = 100
STAMINA_REGEN_RATE = 25  # per second
STAMINA_USE_RATE = 20  # per second while sprinting
SPRINT_SPEED_MULT = 1.35

# Knockback
KNOCKBACK_SPEED = 420  # pixels per second pushed back
KNOCKBACK_DURATION = 0.18  # seconds of knockback

# Screen shake
SHAKE_INTENSITY = 8
SHAKE_DURATION = 0.15

# Shield
SHIELD_LENGTH = 36  # how far the shield extends forward
SHIELD_WIDTH = 36  # how wide the shield looks
SHIELD_DISTANCE = PLAYER_RADIUS - 6
SHIELD_MAX_BLOCKS = 5

# Potions and coins
POTION_HEAL = 30
START_POTION_COUNT = 0
COIN_VALUE = 5
COIN_PICKUP_RADIUS = 50
SPEED_POTION_COST = 10
SPEED_BOOST_MULT = 1.5

# Inventory
INVENTORY_SLOTS = 10

# Doors
DOOR_WIDTH = 40
DOOR_HEIGHT = 120
DOOR_MARGIN = 10
FIRST_ROOM_DOOR_WIDTH = 120
FIRST_ROOM_DOOR_HEIGHT = 180
FIRST_ROOM_DOOR_COLOR = (255, 255, 80)
FIRST_ROOM_DOOR_OUTLINE = (255, 255, 255)

# Visuals
FONT_SIZE = 26
BLOOD_LIFETIME = 0.6

# Dodge
DODGE_DURATION = 0.25
DODGE_COOLDOWN = 1.0
DODGE_SPEED_MULT = 2.2

# Shopkeeper / map
MAP_SIZE = 240
NPC_WIDTH = 48
NPC_HEIGHT = 64

# Dialogue
DIALOGUE_CHARS_PER_SEC = 60

# Spirit reward
SPIRIT_HEALTH_BONUS = 20
