# view/melee_menu_renderer.py
# [2026-02-03] reason: sprite-based control rendering with anchor-based scaling from 320x240 layout.

import os
import pygame
from project.config import SCREEN_W, SCREEN_H
from project.ships.registry import SHIP_CLASSES


DEBUG_GRID = True
AUTO_ANCHOR_MODE = False

# [2026-02-03] reason: base UQM menu resolution for anchor conversion.
BASE_W = 320
BASE_H = 240
TEAM1_POS = (289, 39)
TEAM2_POS = (289, 182)
# [2026-02-03] reason: anchors for Save/Load/Battle button sprites in 320x240 layout space.
SAVE_T1_POS = (286, 61)
LOAD_T1_POS = (288, 71)
SAVE_T2_POS = (288, 159)
LOAD_T2_POS = (288, 149)
BATTLE_POS = (288, 110)

# [2026-03-16] Причина: базовая геометрия двух сеток флота (320x240) для procedural-отрисовки слотов.
TEAM1_GRID_RECT = pygame.Rect(8, 58, 206, 82)
TEAM2_GRID_RECT = pygame.Rect(8, 151, 206, 82)
GRID_COLS = 7
GRID_ROWS = 2

# [2026-03-17] Причина: базовая геометрия полей имён команд в main menu.
TEAM1_NAME_RECT = pygame.Rect(8, 44, 130, 12)
TEAM2_NAME_RECT = pygame.Rect(8, 137, 130, 12)

# [2026-03-17] Причина: базовая геометрия области preview внутри существующего BATTLE-спрайта (320x240).
BATTLE_AREA_RECT = pygame.Rect(220, 78, 96, 148)
METER_SEGMENTS = 10
METER_CUBE_SIZE = 4
METER_CUBE_GAP = 1
METER_MAX_UNITS = 42
CARD_TITLE_RECT = pygame.Rect(8, 6, 80, 14)
CARD_ICON_RECT = pygame.Rect(16, 24, 64, 60)
CARD_CREW_METER_RECT = pygame.Rect(8, 30, 9, 84)
CARD_BATT_METER_RECT = pygame.Rect(79, 30, 9, 84)
CARD_CREW_LABEL_RECT = pygame.Rect(2, 108, 28, 10)
CARD_CREW_VALUE_RECT = pygame.Rect(6, 113, 20, 10)
CARD_BATT_LABEL_RECT = pygame.Rect(66, 108, 28, 10)
CARD_BATT_VALUE_RECT = pygame.Rect(71, 113, 20, 10)
CARD_COST_LABEL_RECT = pygame.Rect(34, 104, 28, 10)
CARD_COST_VALUE_RECT = pygame.Rect(35, 98, 26, 12)
CARD_EMPTY_RECT = pygame.Rect(12, 58, 72, 16)
CARD_TEAM_RECT = pygame.Rect(16, 58, 64, 16)

# [2026-02-03] reason: control option order must match menu logic values.
CONTROL_OPTIONS = [
    "Human Control",
    "Weak Cyborg",
    "Good Cyborg",
    "Awesome Cyborg",
]

# [2026-03-16] Причина: соответствие игровых названий кораблей и доступных иконок меню.
SHIP_ICON_FILES = {
    "EARTHLING CRUISER": os.path.join("assets", "ui", "icons", "melee", "cruiser-icons-001.png"),
    "KOHR-AH MARAUDER": os.path.join("assets", "ui", "icons", "melee", "marauder-icons-001.png"),
    "YEHAT TERMINATOR": os.path.join("assets", "ui", "icons", "melee", "terminator-icons-001.png"),
}

ICON_SCALE_OVERRIDES = {
    "EARTHLING CRUISER": 1.08,
    "KOHR-AH MARAUDER": 0.94,
    "YEHAT TERMINATOR": 1.12,
}


class MeleeMenuRenderer:
    def __init__(self):
        # [2026-02-03] reason: load UQM control sprites 000..008 into dictionary for direct frame access.
        self.ui_sprites = {}
        for frame in [0, 1, 2, 3, 4, 5, 6, 7, 8, 17, 18, 19, 20, 25, 26]:
            self.ui_sprites[frame] = self._load_frame(frame)
        # [2026-02-03] reason: diagnostic click-capture flow for automatic button anchor picking.
        self._anchor_targets = [
            "SAVE_T1",
            "LOAD_T1",
            "SAVE_T2",
            "LOAD_T2",
            "BATTLE"
        ]
        self._captured = {}
        self._anchor_step = 0

        # [2026-03-16] Причина: шрифты и кэш для ship icon/preview rendering.
        self._slot_font = pygame.font.SysFont("Arial", 10)
        self._preview_font = pygame.font.SysFont("Arial", 13)
        self._preview_title_font = pygame.font.SysFont("Arial", 14, bold=True)
        self._ship_icon_cache = {}
        self._ship_icon_scaled_cache = {}
        self._ship_stats_cache = {}

    def _frame_path(self, frame_index):
        return os.path.join("assets", "ui", "menu", f"meleemenu-{frame_index:03d}.png")

    def _load_frame(self, frame_index):
        # [2026-02-03] reason: safe loading with transparent fallback avoids runtime break when asset is missing.
        path = self._frame_path(frame_index)
        if os.path.exists(path):
            return pygame.image.load(path).convert_alpha()
        fallback = pygame.Surface((1, 1), pygame.SRCALPHA)
        fallback.fill((0, 0, 0, 0))
        return fallback

    # [2026-03-16] Причина: единая конвертация Rect из 320x240 в текущее экранное разрешение.
    def _scale_rect(self, rect, scale_x, scale_y):
        return pygame.Rect(
            int(rect.x * scale_x),
            int(rect.y * scale_y),
            max(1, int(rect.width * scale_x)),
            max(1, int(rect.height * scale_y)),
        )

    # [2026-03-16] Причина: определение, выбран ли конкретный слот по данным состояния menu.py.
    def _is_slot_selected(self, menu, team_name, slot_index):
        return (
            getattr(menu, "selected_right", -1) == -1
            and getattr(menu, "selected_team", "") == team_name
            and getattr(menu, "selected_slot", -1) == slot_index
        )

    # [2026-03-16] Причина: procedural-отрисовка ячейки (empty/filled + blink) без новых ассетов.
    def _draw_slot(self, screen, rect, filled, blink_on, selected):
        if filled:
            fill_color = (40, 90, 165) if not (selected and blink_on) else (80, 150, 240)
            border_color = (70, 140, 220) if not (selected and blink_on) else (170, 225, 255)
        else:
            fill_color = (22, 30, 52) if not (selected and blink_on) else (48, 70, 110)
            border_color = (40, 90, 165) if not (selected and blink_on) else (130, 200, 255)

        pygame.draw.rect(screen, fill_color, rect)
        pygame.draw.rect(screen, border_color, rect, max(1, rect.width // 14))

    # [2026-03-17] Причина: контекстная подсветка поля имени команды при выборе заголовка команды.
    def _get_display_team_name(self, menu, team_name):
        if (
            getattr(menu, "editing_team", False)
            and getattr(menu, "selected_team", "") == team_name
        ):
            live_name = getattr(menu, "editing_team_name", "")
            return f"{live_name}_"

        name_value = menu.team_names.get(team_name, "")
        if not str(name_value).strip():
            return "TEAM 1" if team_name == "Team 1" else "TEAM 2"
        return str(name_value)

    def _draw_team_name(self, menu, screen, team_name, base_rect, scale_x, scale_y):
        rect = self._scale_rect(base_rect, scale_x, scale_y)
        name_value = self._get_display_team_name(menu, team_name)

        selected_header = (
            getattr(menu, "selected_right", -1) == -1
            and getattr(menu, "selected_team", "") == team_name
            and getattr(menu, "selected_slot", -1) == -1
        )

        bg_col = (20, 40, 84) if selected_header else (8, 20, 52)
        br_col = (130, 200, 255) if selected_header else (50, 90, 160)
        pygame.draw.rect(screen, bg_col, rect)
        pygame.draw.rect(screen, br_col, rect, 1)

        text_surface = self._preview_font.render(name_value, True, (230, 240, 255))
        text_pos = (
            rect.x + 3,
            rect.y + max(0, (rect.height - text_surface.get_height()) // 2),
        )
        screen.blit(text_surface, text_pos)

    # [2026-03-16] Причина: безопасная нормализация имени корабля для маппинга иконок.
    def _normalize_ship_key(self, ship_name):
        if not ship_name:
            return ""
        return str(ship_name).strip().upper()

    # [2026-03-16] Причина: получение оригинальной иконки корабля из ассетов с кэшированием.
    def _get_ship_icon_surface(self, ship_name):
        key = self._normalize_ship_key(ship_name)
        if not key:
            return None

        if key in self._ship_icon_cache:
            return self._ship_icon_cache[key]

        icon_path = SHIP_ICON_FILES.get(key)
        if icon_path and os.path.exists(icon_path):
            try:
                icon = pygame.image.load(icon_path).convert_alpha()
            except Exception:
                icon = None
        else:
            icon = None

        self._ship_icon_cache[key] = icon
        return icon

    # [2026-03-16] Причина: масштабирование иконки корабля под слот с кэшированием результата.
    def _get_scaled_ship_icon(self, ship_name, target_w, target_h):
        key = self._normalize_ship_key(ship_name)
        if not key:
            return None

        cache_key = (key, target_w, target_h)
        if cache_key in self._ship_icon_scaled_cache:
            return self._ship_icon_scaled_cache[cache_key]

        source = self._get_ship_icon_surface(ship_name)
        if source is None:
            self._ship_icon_scaled_cache[cache_key] = None
            return None

        src_w, src_h = source.get_size()
        if src_w <= 0 or src_h <= 0:
            self._ship_icon_scaled_cache[cache_key] = None
            return None

        scale = min(target_w / src_w, target_h / src_h)
        scale *= ICON_SCALE_OVERRIDES.get(key, 1.0)
        scaled_w = max(1, min(target_w, int(src_w * scale)))
        scaled_h = max(1, min(target_h, int(src_h * scale)))
        scaled = pygame.transform.smoothscale(source, (scaled_w, scaled_h))
        self._ship_icon_scaled_cache[cache_key] = scaled
        return scaled

    # [2026-03-17] Причина: получение статистики корабля для preview panel из существующей модели.
    def _get_ship_stats(self, ship_name):
        key = self._normalize_ship_key(ship_name)
        if not key:
            return None
        if key in self._ship_stats_cache:
            return self._ship_stats_cache[key]

        ship_cls = SHIP_CLASSES.get(ship_name)
        if ship_cls is None:
            self._ship_stats_cache[key] = None
            return None

        try:
            probe = ship_cls(0, 0, (255, 255, 255))
            max_crew = int(getattr(probe, "max_crew", 0) or 0)
            max_batt = int(getattr(probe, "max_energy", 0) or 0)
            cost = int(getattr(probe, "cost", max_crew if max_crew > 0 else 0) or 0)
            stats = {
                "name": getattr(probe, "name", ship_name),
                "crew": int(getattr(probe, "crew", max_crew) or 0),
                "max_crew": max_crew,
                "batt": int(getattr(probe, "energy", max_batt) or 0),
                "max_batt": max_batt,
                "cost": cost,
            }
        except Exception:
            stats = {
                "name": ship_name,
                "crew": 0,
                "max_crew": 0,
                "batt": 0,
                "max_batt": 0,
                "cost": 0,
            }

        self._ship_stats_cache[key] = stats
        return stats

    # [2026-03-16] Причина: рисование иконки корабля в пределах слота с приоритетом реальных ассетов.
    def _draw_ship_icon_in_slot(self, screen, ship_name, rect):
        if not ship_name:
            return

        inset_x = max(2, rect.width // 10)
        inset_y = max(2, rect.height // 10)
        target_w = max(4, rect.width - inset_x * 2)
        target_h = max(4, rect.height - inset_y * 2)
        ship_icon = self._get_scaled_ship_icon(ship_name, target_w, target_h)

        if ship_icon is not None:
            icon_x = rect.centerx - ship_icon.get_width() // 2
            icon_y = rect.centery - ship_icon.get_height() // 2
            screen.blit(ship_icon, (icon_x, icon_y))
            return

        # [2026-03-16] Причина: fallback для неизвестного корабля при отсутствии ассета.
        icon_w = max(4, rect.width // 2)
        icon_h = max(4, rect.height // 2)
        icon_rect = pygame.Rect(
            rect.centerx - icon_w // 2,
            rect.centery - icon_h // 2,
            icon_w,
            icon_h,
        )
        pygame.draw.rect(screen, (210, 235, 255), icon_rect)
        pygame.draw.rect(screen, (8, 30, 80), icon_rect, 1)

        short = str(ship_name)[:2].upper()
        txt = self._slot_font.render(short, True, (8, 30, 80))
        txt_pos = (
            icon_rect.centerx - txt.get_width() // 2,
            icon_rect.centery - txt.get_height() // 2,
        )
        screen.blit(txt, txt_pos)

    # [2026-03-16] Причина: отрисовка сетки команды 2x7 и визуального blink выбранного слота.
    def _draw_team_grid(self, menu, screen, team_name, base_rect, scale_x, scale_y, blink_on):
        scaled_rect = self._scale_rect(base_rect, scale_x, scale_y)
        cols = GRID_COLS
        rows = GRID_ROWS
        slots_count = min(getattr(menu, "team_slots", 14), cols * rows)

        gap_x = max(2, scaled_rect.width // 100)
        gap_y = max(2, scaled_rect.height // 18)
        slot_w = max(6, (scaled_rect.width - gap_x * (cols - 1)) // cols)
        slot_h = max(6, (scaled_rect.height - gap_y * (rows - 1)) // rows)

        team_slots = menu.teams.get(team_name, [])

        for slot_index in range(slots_count):
            row = slot_index // cols
            col = slot_index % cols
            slot_rect = pygame.Rect(
                scaled_rect.x + col * (slot_w + gap_x),
                scaled_rect.y + row * (slot_h + gap_y),
                slot_w,
                slot_h,
            )

            ship_name = team_slots[slot_index] if slot_index < len(team_slots) else None
            filled = ship_name is not None
            selected = self._is_slot_selected(menu, team_name, slot_index)

            self._draw_slot(screen, slot_rect, filled, blink_on, selected)
            if filled:
                self._draw_ship_icon_in_slot(screen, ship_name, slot_rect)

    # [2026-03-19] Причина: вычисление взаимоисключающего режима содержимого правой context-панели.
    def _get_right_panel_mode(self, menu):
        if getattr(menu, "selected_right", -1) == -1:
            team_name = getattr(menu, "selected_team", "Team 1")
            slot_index = getattr(menu, "selected_slot", -1)

            if slot_index == -1:
                return {
                    "kind": "team_name",
                    "team": team_name,
                    "label": "TEAM NAME",
                }

            team_slots = menu.teams.get(team_name, [])
            ship_name = team_slots[slot_index] if 0 <= slot_index < len(team_slots) else None
            if ship_name:
                return {
                    "kind": "ship",
                    "team": team_name,
                    "slot": slot_index,
                    "ship_name": ship_name,
                }
            return {
                "kind": "empty",
                "team": team_name,
                "slot": slot_index,
                "label": "EMPTY SLOT",
            }

        return {
            "kind": "none",
            "label": "",
        }

    # [2026-03-20] Причина: CREW/BATT meters должны использовать фиксированный размер cube-блока; stat влияет только на число блоков.
    def _draw_vertical_meter(self, screen, rect, value, max_value, active_color, inactive_color):
        units = max(0, int(value or 0))
        if units <= 0:
            return

        cols = 2
        rows = max(1, (units + cols - 1) // cols)
        block_size = METER_CUBE_SIZE
        gap = METER_CUBE_GAP

        content_w = cols * block_size + gap * (cols - 1)
        content_h = rows * block_size + gap * (rows - 1)
        start_x = rect.x + max(0, (rect.width - content_w) // 2)
        start_y = rect.bottom - content_h

        bg_pad = 1
        bg_rect = pygame.Rect(
            start_x - bg_pad,
            start_y - bg_pad,
            content_w + bg_pad * 2,
            content_h + bg_pad * 2,
        )
        pygame.draw.rect(screen, (0, 0, 0), bg_rect)
        pygame.draw.rect(screen, (70, 70, 70), bg_rect, 1)

        edge_color = tuple(max(0, c - 60) for c in active_color)
        highlight_color = tuple(min(255, c + 35) for c in active_color)

        for unit_index in range(units):
            row = unit_index // cols
            col = unit_index % cols
            block_rect = pygame.Rect(
                start_x + col * (block_size + gap),
                start_y + content_h - block_size - row * (block_size + gap),
                block_size,
                block_size,
            )
            pygame.draw.rect(screen, active_color, block_rect)
            pygame.draw.rect(screen, edge_color, block_rect, 1)
            if block_rect.width > 2 and block_rect.height > 2:
                highlight = pygame.Rect(block_rect.x + 1, block_rect.y + 1, block_rect.width - 2, max(1, block_rect.height // 3))
                pygame.draw.rect(screen, highlight_color, highlight)

    # [2026-03-20] Причина: ship context card должен использовать фиксированный UQM-style sub-layout, а не адаптивное размещение по контенту.
    def _scale_card_local_rect(self, panel_rect, local_rect):
        rel_x = local_rect.x / BATTLE_AREA_RECT.width
        rel_y = local_rect.y / BATTLE_AREA_RECT.height
        rel_w = local_rect.width / BATTLE_AREA_RECT.width
        rel_h = local_rect.height / BATTLE_AREA_RECT.height
        return pygame.Rect(
            panel_rect.x + int(panel_rect.width * rel_x),
            panel_rect.y + int(panel_rect.height * rel_y),
            max(1, int(panel_rect.width * rel_w)),
            max(1, int(panel_rect.height * rel_h)),
        )

    # [2026-03-20] Причина: построение внутренних sub-rect ship card по фиксированной пиксельной раскладке оригинального preview card.
    def _build_battle_panel_subrects(self, panel_rect):
        return {
            "title": self._scale_card_local_rect(panel_rect, CARD_TITLE_RECT),
            "icon": self._scale_card_local_rect(panel_rect, CARD_ICON_RECT),
            "crew_meter": self._scale_card_local_rect(panel_rect, CARD_CREW_METER_RECT),
            "batt_meter": self._scale_card_local_rect(panel_rect, CARD_BATT_METER_RECT),
            "crew_label": self._scale_card_local_rect(panel_rect, CARD_CREW_LABEL_RECT),
            "crew_value": self._scale_card_local_rect(panel_rect, CARD_CREW_VALUE_RECT),
            "batt_label": self._scale_card_local_rect(panel_rect, CARD_BATT_LABEL_RECT),
            "batt_value": self._scale_card_local_rect(panel_rect, CARD_BATT_VALUE_RECT),
            "cost_label": self._scale_card_local_rect(panel_rect, CARD_COST_LABEL_RECT),
            "cost_value": self._scale_card_local_rect(panel_rect, CARD_COST_VALUE_RECT),
            "empty": self._scale_card_local_rect(panel_rect, CARD_EMPTY_RECT),
            "team": self._scale_card_local_rect(panel_rect, CARD_TEAM_RECT),
        }

    # [2026-03-19] Причина: clean procedural background для non-default context panel без crop/subsurface из общего menu background.
    def _draw_context_panel_background(self, screen, panel_rect):
        outer = panel_rect.copy()
        pygame.draw.rect(screen, (120, 124, 138), outer)
        pygame.draw.rect(screen, (185, 190, 205), outer, 1)

        inner = outer.inflate(-max(4, outer.width // 14), -max(4, outer.height // 16))
        pygame.draw.rect(screen, (148, 150, 156), inner)
        pygame.draw.rect(screen, (210, 214, 220), inner, 1)

        content = inner.inflate(-max(2, inner.width // 18), -max(2, inner.height // 18))
        pygame.draw.rect(screen, (122, 126, 134), content)
        pygame.draw.rect(screen, (94, 98, 108), content, 1)

    # [2026-03-17] Причина: context-sensitive контент привязан к фактическому rect panel и рисуется только для preview-режимов.
    def _draw_battle_area_content(self, menu, screen, panel_rect, ctx):
        sub = self._build_battle_panel_subrects(panel_rect)

        if ctx["kind"] == "ship":
            ship_name = ctx["ship_name"]
            stats = self._get_ship_stats(ship_name)
            title = stats["name"] if stats else ship_name
            title_surface = self._preview_title_font.render(title, True, (230, 240, 255))
            title_pos = (
                sub["title"].x,
                sub["title"].y + max(0, (sub["title"].height - title_surface.get_height()) // 2),
            )
            screen.blit(title_surface, title_pos)

            icon_rect = sub["icon"]

            ship_icon = self._get_scaled_ship_icon(
                ship_name,
                max(8, icon_rect.width),
                max(8, icon_rect.height),
            )
            if ship_icon is not None:
                icon_pos = (
                    icon_rect.centerx - ship_icon.get_width() // 2,
                    icon_rect.centery - ship_icon.get_height() // 2,
                )
                screen.blit(ship_icon, icon_pos)
            else:
                self._draw_ship_icon_in_slot(screen, ship_name, icon_rect)

            crew = stats["crew"] if stats else 0
            max_crew = stats["max_crew"] if stats else 0
            batt = stats["batt"] if stats else 0
            max_batt = stats["max_batt"] if stats else 0
            cost = stats["cost"] if stats else 0

            cost_txt = self._preview_font.render(str(cost), True, (220, 230, 255))
            cost_pos = (
                sub["cost_value"].centerx - cost_txt.get_width() // 2,
                sub["cost_value"].y,
            )
            screen.blit(cost_txt, cost_pos)

            crew_lbl = self._preview_font.render("CREW", True, (190, 245, 190))
            batt_lbl = self._preview_font.render("BATT", True, (255, 190, 190))
            screen.blit(crew_lbl, (sub["crew_label"].x, sub["crew_label"].y))
            screen.blit(batt_lbl, (sub["batt_label"].x, sub["batt_label"].y))

            self._draw_vertical_meter(screen, sub["crew_meter"], crew, max_crew, (70, 220, 70), (22, 55, 22))
            self._draw_vertical_meter(screen, sub["batt_meter"], batt, max_batt, (220, 70, 70), (55, 22, 22))
            return

        if ctx["kind"] == "empty":
            label = self._preview_title_font.render("EMPTY SLOT", True, (230, 240, 255))
            label_pos = (
                sub["empty"].centerx - label.get_width() // 2,
                sub["empty"].y,
            )
            screen.blit(label, label_pos)
            return

        if ctx["kind"] == "team_name":
            label = self._preview_title_font.render("TEAM NAME", True, (230, 240, 255))
            label_pos = (
                sub["title"].centerx - label.get_width() // 2,
                sub["title"].y,
            )
            screen.blit(label, label_pos)
            team = ctx.get("team", "Team 1")
            team_name = self._get_display_team_name(menu, team)
            team_text = self._preview_font.render(team_name, True, (200, 220, 255))
            team_pos = (
                sub["team"].centerx - team_text.get_width() // 2,
                sub["team"].y,
            )
            screen.blit(team_text, team_pos)

    def draw_background(self, screen, frame_index):
        # [2026-02-03] reason: compatibility API keeps external calls stable.
        bg = self.ui_sprites[0]
        bg_scaled = pygame.transform.scale(bg, (SCREEN_W, SCREEN_H))
        screen.blit(bg_scaled, (0, 0))

    def draw_main_menu(self, menu):
        # [2026-02-03] reason: render background full-screen and place controls by scaled 320x240 anchors.
        screen = menu.screen

        bg = self.ui_sprites[0]
        bg_scaled = pygame.transform.scale(bg, (SCREEN_W, SCREEN_H))
        screen.blit(bg_scaled, (0, 0))

        scale_x = SCREEN_W / BASE_W
        scale_y = SCREEN_H / BASE_H

        if AUTO_ANCHOR_MODE:
            # [2026-02-03] reason: capture Save/Load/Battle anchor centers from mouse clicks in runtime.
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    base_x = int(mx / scale_x)
                    base_y = int(my / scale_y)

                    key = self._anchor_targets[self._anchor_step]
                    self._captured[key] = (base_x, base_y)
                    print(f"{key} = ({base_x}, {base_y})")

                    self._anchor_step += 1

                    if self._anchor_step >= len(self._anchor_targets):
                        with open("melee_anchor_buttons.txt", "w") as f:
                            for k, v in self._captured.items():
                                f.write(f"{k}_POS = {v}\n")
                        print("All anchors saved to melee_anchor_buttons.txt")
                        self._anchor_step = len(self._anchor_targets) - 1

            font = pygame.font.SysFont(None, 22)

            if self._anchor_step < len(self._anchor_targets):
                msg = f"Click center of {self._anchor_targets[self._anchor_step]}"
            else:
                msg = "All anchors captured. Disable AUTO_ANCHOR_MODE."

            screen.blit(font.render(msg, True, (255, 255, 0)), (20, 20))

        if DEBUG_GRID:
            # [2026-02-03] reason: debug overlay for 320x240 grid and control anchors.
            cell_w = SCREEN_W / BASE_W
            cell_h = SCREEN_H / BASE_H

            for x in range(0, BASE_W, 10):
                px = int(x * cell_w)
                pygame.draw.line(screen, (40, 40, 40), (px, 0), (px, SCREEN_H))

            for y in range(0, BASE_H, 10):
                py = int(y * cell_h)
                pygame.draw.line(screen, (40, 40, 40), (0, py), (SCREEN_W, py))

            t1x = int(TEAM1_POS[0] * scale_x)
            t1y = int(TEAM1_POS[1] * scale_y)
            pygame.draw.circle(screen, (255, 0, 0), (t1x, t1y), 6)

            t2x = int(TEAM2_POS[0] * scale_x)
            t2y = int(TEAM2_POS[1] * scale_y)
            pygame.draw.circle(screen, (0, 255, 0), (t2x, t2y), 6)

        # [2026-03-17] Причина: имена команд должны быть видны и подсвечиваться при выборе header-поля.
        self._draw_team_name(menu, screen, "Team 1", TEAM1_NAME_RECT, scale_x, scale_y)
        self._draw_team_name(menu, screen, "Team 2", TEAM2_NAME_RECT, scale_x, scale_y)

        # [2026-03-16] Причина: визуальный blink выбранного слота без изменения состояния menu.py.
        blink_on = (pygame.time.get_ticks() // 250) % 2 == 0
        self._draw_team_grid(menu, screen, "Team 1", TEAM1_GRID_RECT, scale_x, scale_y, blink_on)
        self._draw_team_grid(menu, screen, "Team 2", TEAM2_GRID_RECT, scale_x, scale_y, blink_on)

        team1_x = int(TEAM1_POS[0] * scale_x)
        team1_y = int(TEAM1_POS[1] * scale_y)
        team2_x = int(TEAM2_POS[0] * scale_x)
        team2_y = int(TEAM2_POS[1] * scale_y)

        # Team 1 control sprite
        team1_idx = CONTROL_OPTIONS.index(menu.settings["Team 1"]["control"])
        if menu.selected_right == 0:
            team1_sprite = 1 + team1_idx
        else:
            team1_sprite = 5 + team1_idx
        # [2026-02-03] reason: control sprite must scale with background scale factors.
        # [2026-02-03] reason: anchor is slot center, so scaled sprite is centered on anchor.
        team1_img = self.ui_sprites[team1_sprite]
        team1_scaled = pygame.transform.scale(
            team1_img,
            (
                int(team1_img.get_width() * scale_x),
                int(team1_img.get_height() * scale_y),
            ),
        )
        screen.blit(
            team1_scaled,
            (
                team1_x - team1_scaled.get_width() // 2,
                team1_y - team1_scaled.get_height() // 2,
            ),
        )

        # Team 2 control sprite
        team2_idx = CONTROL_OPTIONS.index(menu.settings["Team 2"]["control"])
        if menu.selected_right == 6:
            team2_sprite = 1 + team2_idx
        else:
            team2_sprite = 5 + team2_idx
        # [2026-02-03] reason: control sprite must scale with background scale factors.
        # [2026-02-03] reason: anchor is slot center, so scaled sprite is centered on anchor.
        team2_img = self.ui_sprites[team2_sprite]
        team2_scaled = pygame.transform.scale(
            team2_img,
            (
                int(team2_img.get_width() * scale_x),
                int(team2_img.get_height() * scale_y),
            ),
        )
        screen.blit(
            team2_scaled,
            (
                team2_x - team2_scaled.get_width() // 2,
                team2_y - team2_scaled.get_height() // 2,
            ),
        )

        # [2026-02-03] reason: selected_right drives Save/Load/Battle sprite states without changing menu logic.
        selected = menu.selected_right

        if selected == 1:
            save_t1_frame = 20
        else:
            save_t1_frame = 18
        save_t1_x = int(SAVE_T1_POS[0] * scale_x)
        save_t1_y = int(SAVE_T1_POS[1] * scale_y)
        save_t1_img = self.ui_sprites[save_t1_frame]
        save_t1_scaled = pygame.transform.scale(
            save_t1_img,
            (
                int(save_t1_img.get_width() * scale_x),
                int(save_t1_img.get_height() * scale_y),
            ),
        )
        screen.blit(
            save_t1_scaled,
            (
                save_t1_x - save_t1_scaled.get_width() // 2,
                save_t1_y - save_t1_scaled.get_height() // 2,
            ),
        )

        if selected == 2:
            load_t1_frame = 19
        else:
            load_t1_frame = 17
        load_t1_x = int(LOAD_T1_POS[0] * scale_x)
        load_t1_y = int(LOAD_T1_POS[1] * scale_y)
        load_t1_img = self.ui_sprites[load_t1_frame]
        load_t1_scaled = pygame.transform.scale(
            load_t1_img,
            (
                int(load_t1_img.get_width() * scale_x),
                int(load_t1_img.get_height() * scale_y),
            ),
        )
        screen.blit(
            load_t1_scaled,
            (
                load_t1_x - load_t1_scaled.get_width() // 2,
                load_t1_y - load_t1_scaled.get_height() // 2,
            ),
        )

        if selected == 4:
            save_t2_frame = 20
        else:
            save_t2_frame = 18
        save_t2_x = int(SAVE_T2_POS[0] * scale_x)
        save_t2_y = int(SAVE_T2_POS[1] * scale_y)
        save_t2_img = self.ui_sprites[save_t2_frame]
        save_t2_scaled = pygame.transform.scale(
            save_t2_img,
            (
                int(save_t2_img.get_width() * scale_x),
                int(save_t2_img.get_height() * scale_y),
            ),
        )
        screen.blit(
            save_t2_scaled,
            (
                save_t2_x - save_t2_scaled.get_width() // 2,
                save_t2_y - save_t2_scaled.get_height() // 2,
            ),
        )

        if selected == 5:
            load_t2_frame = 19
        else:
            load_t2_frame = 17
        load_t2_x = int(LOAD_T2_POS[0] * scale_x)
        load_t2_y = int(LOAD_T2_POS[1] * scale_y)
        load_t2_img = self.ui_sprites[load_t2_frame]
        load_t2_scaled = pygame.transform.scale(
            load_t2_img,
            (
                int(load_t2_img.get_width() * scale_x),
                int(load_t2_img.get_height() * scale_y),
            ),
        )
        screen.blit(
            load_t2_scaled,
            (
                load_t2_x - load_t2_scaled.get_width() // 2,
                load_t2_y - load_t2_scaled.get_height() // 2,
            ),
        )

        panel_mode = self._get_right_panel_mode(menu)

        if selected == 3:
            battle_frame = 26
        else:
            battle_frame = 25
        battle_x = int(BATTLE_POS[0] * scale_x)
        battle_y = int(BATTLE_POS[1] * scale_y)
        battle_img = self.ui_sprites[battle_frame]
        battle_scaled = pygame.transform.scale(
            battle_img,
            (
                int(battle_img.get_width() * scale_x),
                int(battle_img.get_height() * scale_y),
            ),
        )
        battle_rect = pygame.Rect(
            battle_x - battle_scaled.get_width() // 2,
            battle_y - battle_scaled.get_height() // 2,
            battle_scaled.get_width(),
            battle_scaled.get_height(),
        )

        if panel_mode["kind"] == "none":
            screen.blit(battle_scaled, battle_rect.topleft)
        else:
            # [2026-03-19] Причина: preview/empty/team modes должны переключать содержимое panel, а не наслаиваться на BATTLE!-состояние.
            self._draw_context_panel_background(screen, battle_rect)
            self._draw_battle_area_content(menu, screen, battle_rect, panel_mode)
