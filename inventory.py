from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

import settings
from hud import draw_potion_icon

if TYPE_CHECKING:
    from game_state import GameState
    from player import PlayerState

EQUIPMENT_SLOT_MAP = {
    "Traveler Hood": "head",
    "Explorer Cap": "head",
    "Cloth Tunic": "body",
    "Leather Armor": "body",
    "Traveler Pants": "legs",
    "Runner Boots": "legs",
        "Sword": "weapon",
        "Shield": "shield",
    "Bacon of the Dead": "summon",
}
ARMOR_ITEMS = {"Leather Armor"}


def _render_text_lines(text: str, primary_font: pygame.font.Font, fallback_font: pygame.font.Font, max_width: int, color=(255, 255, 255)):
    """
    Render text that fits inside max_width. If a space exists, render as two lines (split on first space)
    to keep the full text readable without ellipses.
    """
    primary = primary_font.render(text, True, color)
    if primary.get_width() <= max_width:
        return [primary]
    # Try splitting into two lines on the first space
    if " " in text:
        first, second = text.split(" ", 1)
        line_font = fallback_font
        l1 = line_font.render(first, True, color)
        l2 = line_font.render(second, True, color)
        if l1.get_width() <= max_width and l2.get_width() <= max_width:
            return [l1, l2]
    # Fallback to single-line with smaller font
    return [fallback_font.render(text, True, color)]


def add_item_to_inventory(state: GameState, item: str):
    """Put an item in the first empty slot (overwrite the last slot if needed)."""
    for i, current in enumerate(state.inventory):
        if current == "":
            state.inventory[i] = item
            return
    state.inventory[-1] = item


def apply_equipment_effects(player: PlayerState):
    """Recalculate derived flags from equipment choices."""
    player.armor_equipped = player.body_item in ARMOR_ITEMS


def equip_item_from_inventory(state: GameState, slot_index: int) -> bool:
    """Swap an inventory item into the correct equipment slot, returning True if equipped/unequipped."""
    if slot_index < 0 or slot_index >= len(state.inventory):
        return False
    item = state.inventory[slot_index]
    player = state.player
    
    # Handle Bow as a special toggle (equip/unequip)
    if item == "Bow":
        player.bow_equipped = not player.bow_equipped
        return True
    
    # Handle Speed Potion as a special toggle (equip/unequip)
    if item == "Speed Potion":
        player.speed_potion_equipped = not getattr(player, "speed_potion_equipped", False)
        return True
    
    equip_slot = EQUIPMENT_SLOT_MAP.get(item)
    if not equip_slot:
        return False
    attr = f"{equip_slot}_item"
    current_equipped = getattr(player, attr, "")
    
    # If already equipped, unequip it (item stays in inventory)
    if current_equipped == item:
        setattr(player, attr, "")
        apply_equipment_effects(player)
        return True
    
    # Equip this item, replacing any currently equipped item in that slot
    setattr(player, attr, item)
    apply_equipment_effects(player)
    return True


def ensure_default_equipment(player: PlayerState):
    """Recalculate equipment flags without forcing default gear."""
    apply_equipment_effects(player)


def get_inventory_layout(screen: pygame.Surface):
    """Compute shared geometry for the inventory/equipment overlay.

    Layout is computed proportional to the screen so the inventory panel
    stays centered and scales on different resolutions.
    """
    screen_w, screen_h = screen.get_width(), screen.get_height()
    # Base sizes (slot sizes remain reasonable on small screens)
    slot_w, slot_h = 72, 72
    button_h = 22
    row_gap = 12

    # Proportional panel size (centered)
    panel_w = int(screen_w * 0.78)
    panel_h = int(screen_h * 0.68)
    padding = 16

    # Profile column takes a fraction of panel width
    profile_width = int(panel_w * 0.24)
    # Gap between columns
    gap = 18

    # Remaining width for three columns
    inner_w = panel_w - padding * 2 - profile_width - gap
    col_w = int((inner_w - gap * 3) / 4)

    start_x = (screen_w - panel_w) // 2
    inv_x = start_x + padding
    inv_y = (screen_h - panel_h) // 2 + 24

    rows = math.ceil(settings.INVENTORY_SLOTS / 5)
    row_height = slot_h + button_h + row_gap
    panel_height = panel_h

    return {
        "slot_w": slot_w,
        "slot_h": slot_h,
        "margin": 12,
        "button_h": button_h,
        "row_gap": row_gap,
        "row_height": row_height,
        "cols": 5,
        "rows": rows,
        "inv_width": inner_w,
        "inv_height": panel_h - 80,
        "inv_x": inv_x,
        "inv_y": inv_y,
        "gap": gap,
        "profile_width": profile_width,
        "profile_x": start_x + panel_w - padding - profile_width,
        "panel_height": panel_height,
        "start_x": start_x,
        "panel_w": panel_w,
        "panel_h": panel_h,
        "col_w": col_w,
    }


def get_grouped_slot_rects(state: "GameState") -> dict:
    """Return a mapping of inventory index -> pygame.Rect for the grouped inventory UI.
    Also returns a list of action buttons as tuples (index, rect, action_type).
    action_type is one of: 'equip', 'bow_toggle', 'use_potion'
    """
    screen = state.screen
    layout = get_inventory_layout(screen)
    start_x = layout["inv_x"]
    inv_y = layout["inv_y"]
    col_w = layout.get("col_w", 140)
    gap = layout.get("gap", 18)
    # compute three column x positions inside the panel area
    col_x = [start_x + i * (col_w + gap) for i in range(4)]
    slot_h = 56
    row_gap = layout.get("row_gap", 12)

    index_rects = {}
    buttons = []

    # Build grouped lists with original indices
    armor = []
    shields = []
    weapons = []
    potions = []
    for i, item in enumerate(state.inventory):
        if not item:
            continue
        if item in ("Bow", "Sword", "Bacon of the Dead"):
            weapons.append((i, item))
        elif item in ("Speed Potion", "Health Potion"):
            potions.append((i, item))
        elif item == "Shield":
            shields.append((i, item))
        elif item in EQUIPMENT_SLOT_MAP.keys():
            armor.append((i, item))
        else:
            # put unknowns into weapons by default
            weapons.append((i, item))

    # For each column, create rects stacked vertically
    def place_list(items, col_index):
        y = inv_y + 40
        for idx, (i, item) in enumerate(items):
            rect = pygame.Rect(col_x[col_index], int(y), col_w, slot_h)
            index_rects[i] = rect
            # add button rect below
            btn_rect = pygame.Rect(rect.x + 6, rect.bottom + 6, rect.width - 12, layout["button_h"])
            if item in ("Bow", "Sword"):
                buttons.append((i, btn_rect, "equip"))
            elif item in ("Speed Potion", "Health Potion"):
                buttons.append((i, btn_rect, "use_potion"))
            elif item in EQUIPMENT_SLOT_MAP.keys():
                buttons.append((i, btn_rect, "equip"))
            else:
                buttons.append((i, btn_rect, "none"))
            y += slot_h + layout["button_h"] + row_gap

    place_list(armor, 0)
    place_list(shields, 1)
    place_list(weapons, 2)
    place_list(potions, 3)

    return {"rects": index_rects, "buttons": buttons, "col_x": col_x, "inv_y": inv_y, "col_w": col_w}


def get_slot_rect(layout: dict, index: int) -> pygame.Rect:
    col = index % layout["cols"]
    row = index // layout["cols"]
    x = layout["inv_x"] + col * (layout["slot_w"] + layout["margin"])
    y = layout["inv_y"] + row * layout["row_height"]
    return pygame.Rect(x, y, layout["slot_w"], layout["slot_h"])


def draw_inventory_panel(state: GameState):
    """Render inventory divided into Armor / Weapons / Potions columns plus profile view."""
    screen = state.screen
    player = state.player
    layout = get_inventory_layout(screen)
    inv_font = pygame.font.SysFont(None, 32)
    small_font = pygame.font.SysFont(None, 22)
    padding = 16

    panel_w = layout["panel_w"]
    panel_h = layout["panel_h"]
    panel_left = layout["start_x"]
    panel_top = (screen.get_height() - panel_h) // 2
    # semi-transparent panel surface so background faintly shows through
    panel_surf = pygame.Surface((panel_w + padding * 2, panel_h + padding * 2), pygame.SRCALPHA)
    panel_surf.fill((22, 22, 48, 200))
    # outline
    pygame.draw.rect(panel_surf, (90, 90, 160, 220), panel_surf.get_rect(), 2)
    screen.blit(panel_surf, (panel_left - padding, panel_top - padding))

    inv_title = inv_font.render("Inventory", True, (230, 230, 255))
    # Place the main "Inventory" title centered above the panel
    inv_x = panel_left + panel_w // 2 - inv_title.get_width() // 2
    screen.blit(inv_title, (inv_x, panel_top + 8))

    # panel rect used for separators and positioning
    panel_rect = pygame.Rect(panel_left - padding, panel_top - padding, panel_w + padding * 2, panel_h + padding * 2)
    # column width & gap from layout
    col_w = layout.get("col_w", 140)
    gap = layout.get("gap", 18)

    # Group inventory items preserving indices
    armor = []
    shields = []
    weapons = []
    potions = []
    for i, item in enumerate(state.inventory):
        if not item:
            continue
        if item in ("Bow", "Sword", "Bacon of the Dead"):
            weapons.append((i, item))
        elif item in ("Speed Potion", "Health Potion"):
            potions.append((i, item))
        elif item == "Shield":
            shields.append((i, item))
        elif item in EQUIPMENT_SLOT_MAP.keys():
            armor.append((i, item))
        else:
            weapons.append((i, item))

    col_x = [
        layout["inv_x"],
        layout["inv_x"] + col_w + gap,
        layout["inv_x"] + (col_w + gap) * 2,
        layout["inv_x"] + (col_w + gap) * 3,
    ]
    titles = ["Armor", "Shields", "Weapons", "Potions"]
    lists = [armor, shields, weapons, potions]

    button_regions = []
    # Draw faint separators between the three columns
    sep_x1 = col_x[1] - gap // 2
    sep_x2 = col_x[2] - gap // 2
    sep_x3 = col_x[3] - gap // 2
    pygame.draw.line(screen, (80, 80, 120), (sep_x1, panel_rect.top + 8), (sep_x1, panel_rect.bottom - 8), 2)
    pygame.draw.line(screen, (80, 80, 120), (sep_x2, panel_rect.top + 8), (sep_x2, panel_rect.bottom - 8), 2)
    pygame.draw.line(screen, (80, 80, 120), (sep_x3, panel_rect.top + 8), (sep_x3, panel_rect.bottom - 8), 2)

    for col_i in range(4):
        title_surf = small_font.render(titles[col_i], True, (220, 220, 255))
        screen.blit(title_surf, (col_x[col_i], layout["inv_y"] - 16))
        y = layout["inv_y"] + 40
        for (idx, item) in lists[col_i]:
            rect = pygame.Rect(col_x[col_i], int(y), col_w, 56)
            pygame.draw.rect(screen, (30, 30, 60), rect)
            pygame.draw.rect(screen, (200, 200, 255), rect, 2)
            # draw a small icon left of the item text and render text shifted right
            icon_w = 28
            icon_h = 28
            icon_x = rect.x + 8
            icon_y = rect.y + rect.height // 2 - icon_h // 2
            text_max_w = rect.width - 12 - (icon_w + 8)
            if item == "Speed Potion":
                draw_potion_icon(screen, icon_x, icon_y, enabled="speed")
                lines = _render_text_lines("Speed Potion", inv_font, small_font, text_max_w, (120, 180, 255))
            elif item == "Health Potion":
                draw_potion_icon(screen, icon_x, icon_y, enabled="heal")
                lines = _render_text_lines("Health Potion", inv_font, small_font, text_max_w, (255, 180, 180))
            elif item == "Bow":
                cx = icon_x + icon_w // 2
                cy = icon_y + icon_h // 2
                tri = [
                    (cx - 8, cy + 10),
                    (cx - 8, cy - 10),
                    (cx + 10, cy),
                ]
                pygame.draw.polygon(screen, (200, 200, 255), tri, 0)
                lines = _render_text_lines(item, inv_font, small_font, text_max_w)
            elif item == "Sword":
                sx = icon_x + icon_w // 2
                sy = icon_y + icon_h // 2
                pygame.draw.line(screen, (180, 210, 255), (sx, sy - 10), (sx, sy + 10), 3)
                pygame.draw.circle(screen, (80, 50, 30), (sx, sy + 12), 3)
                lines = _render_text_lines(item, inv_font, small_font, text_max_w)
            elif item == "Shield":
                cx = icon_x + icon_w // 2
                cy = icon_y + icon_h // 2
                base_half = 10
                top = (cx - 14, cy - 6)
                base_l = (cx + base_half, cy - 10)
                base_r = (cx + base_half, cy + 10)
                pygame.draw.polygon(screen, (120, 180, 230), [top, base_l, base_r])
                pygame.draw.polygon(screen, (80, 120, 170), [top, base_l, base_r], 2)
                lines = _render_text_lines(item, inv_font, small_font, text_max_w)
            elif item in EQUIPMENT_SLOT_MAP.keys():
                ax = icon_x + 4
                ay = icon_y + 6
                pygame.draw.rect(screen, (150, 100, 60), (ax, ay, icon_w - 8, icon_h - 12))
                lines = _render_text_lines(item, inv_font, small_font, text_max_w)
            else:
                pygame.draw.circle(screen, (200, 200, 200), (icon_x + icon_w // 2, icon_y + icon_h // 2), 8)
                lines = _render_text_lines(item, inv_font, small_font, text_max_w)

            # draw text to the right of the icon
            text_start_x = rect.x + 6 + (icon_w + 8)
            total_h = sum(s.get_height() for s in lines)
            yy = rect.centery - total_h // 2
            for surf in lines:
                screen.blit(surf, (text_start_x, yy))
                yy += surf.get_height()

            # action button (only Speed Potion gets a Use button; Health Potion shows only picture/label)
            btn_rect = pygame.Rect(rect.x + 6, rect.bottom + 6, rect.width - 12, layout["button_h"])
            if item == "Bow":
                is_equipped = state.player.bow_equipped
                btn_color = (70, 120, 90) if is_equipped else (50, 80, 130)
                pygame.draw.rect(screen, btn_color, btn_rect, border_radius=4)
                pygame.draw.rect(screen, (200, 220, 255), btn_rect, 2, border_radius=4)
                btn_label = "Unequip" if is_equipped else "Equip"
                btn_text = small_font.render(btn_label, True, (240, 240, 255))
                screen.blit(btn_text, (btn_rect.centerx - btn_text.get_width() // 2, btn_rect.centery - btn_text.get_height() // 2))
                button_regions.append((idx, btn_rect, "equip"))
            elif item == "Sword":
                is_equipped = state.player.weapon_item == "Sword"
                btn_color = (70, 120, 90) if is_equipped else (50, 80, 130)
                pygame.draw.rect(screen, btn_color, btn_rect, border_radius=4)
                pygame.draw.rect(screen, (200, 220, 255), btn_rect, 2, border_radius=4)
                btn_label = "Unequip" if is_equipped else "Equip"
                btn_text = small_font.render(btn_label, True, (240, 240, 255))
                screen.blit(btn_text, (btn_rect.centerx - btn_text.get_width() // 2, btn_rect.centery - btn_text.get_height() // 2))
                button_regions.append((idx, btn_rect, "equip"))
            elif item in EQUIPMENT_SLOT_MAP.keys():
                equip_slot = EQUIPMENT_SLOT_MAP[item]
                attr = f"{equip_slot}_item"
                current_equipped = getattr(state.player, attr, "")
                is_equipped = current_equipped == item
                btn_color = (70, 120, 90) if is_equipped else (50, 80, 130)
                pygame.draw.rect(screen, btn_color, btn_rect, border_radius=4)
                pygame.draw.rect(screen, (200, 220, 255), btn_rect, 2, border_radius=4)
                btn_label = "Unequip" if is_equipped else "Equip"
                btn_text = small_font.render(btn_label, True, (240, 240, 255))
                screen.blit(btn_text, (btn_rect.centerx - btn_text.get_width() // 2, btn_rect.centery - btn_text.get_height() // 2))
                button_regions.append((idx, btn_rect, "equip"))
            elif item == "Speed Potion":
                is_equipped = getattr(state.player, "speed_potion_equipped", False)
                btn_color = (70, 120, 90) if is_equipped else (50, 80, 130)
                pygame.draw.rect(screen, btn_color, btn_rect, border_radius=4)
                pygame.draw.rect(screen, (200, 220, 255), btn_rect, 2, border_radius=4)
                btn_label = "Unequip" if is_equipped else "Equip"
                btn_text = small_font.render(btn_label, True, (240, 240, 255))
                screen.blit(btn_text, (btn_rect.centerx - btn_text.get_width() // 2, btn_rect.centery - btn_text.get_height() // 2))
                button_regions.append((idx, btn_rect, "equip"))
            else:
                # no action
                pass

            # small index number (top-right)
            num = small_font.render(str(idx + 1), True, (180, 180, 180))
            screen.blit(num, (rect.right - 18, rect.y + 6))

            y += 56 + layout["button_h"] + layout["row_gap"]

    # draw profile on the right (reuse existing code)
    profile_rect = pygame.Rect(layout["profile_x"], layout["inv_y"], layout["profile_width"], layout["panel_height"] + 32)
    pygame.draw.rect(screen, (32, 32, 64), profile_rect)
    pygame.draw.rect(screen, (130, 130, 190), profile_rect, 2)
    prof_title = inv_font.render("Profile", True, (230, 230, 255))
    screen.blit(prof_title, (profile_rect.x + 12, profile_rect.y + 8))

    silhouette_center = pygame.Vector2(profile_rect.centerx, profile_rect.y + profile_rect.height * 0.4)
    head_center = (int(silhouette_center.x), int(silhouette_center.y - 50))
    body_center = (int(silhouette_center.x), int(silhouette_center.y))
    leg_center = (int(silhouette_center.x), int(silhouette_center.y + 50))
    head_radius = 26
    body_radius = 32
    leg_radius = 22

    head_color = (220, 190, 140) if player.head_item else (120, 120, 120)
    body_color = (180, 60, 60) if not player.armor_equipped else (150, 100, 60)
    leg_color = (110, 70, 50)
    outline = (240, 240, 255)
    pygame.draw.circle(screen, leg_color, leg_center, leg_radius)
    pygame.draw.circle(screen, body_color, body_center, body_radius)
    pygame.draw.circle(screen, head_color, head_center, head_radius)
    pygame.draw.circle(screen, outline, head_center, head_radius, 2)
    pygame.draw.circle(screen, outline, body_center, body_radius, 2)
    pygame.draw.circle(screen, outline, leg_center, leg_radius, 2)
    if player.armor_equipped:
        pygame.draw.circle(screen, (200, 170, 90), body_center, body_radius - 6, 3)

    slots = [("Head", player.head_item), ("Body", player.body_item), ("Legs", player.legs_item)]
    for idx, (label_text, item_text) in enumerate(slots):
        line = small_font.render(f"{label_text}: {item_text or 'None'}", True, (230, 230, 250))
        screen.blit(line, (profile_rect.x + 12, profile_rect.bottom - 90 + idx * 26))

    # store button regions on state for click handling convenience
    state._inventory_button_regions = button_regions
    # store rects mapping
    grouped = get_grouped_slot_rects(state)
    state._inventory_slot_rects = grouped["rects"]
