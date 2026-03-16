# view/melee_menu_renderer.py
# [2026-02-03] reason: sprite-based control rendering with anchor-based scaling from 320x240 layout.

import os
import pygame
from project.config import SCREEN_W, SCREEN_H


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
        # [2026-03-16] Причина: компактный шрифт для placeholder-иконок кораблей внутри занятых слотов.
        self._slot_font = pygame.font.SysFont("Arial", 10)
        # [2026-03-16] Причина: кэш загруженных оригинальных иконок кораблей для исключения загрузки в горячем цикле.
        self._ship_icon_cache = {}
        # [2026-03-16] Причина: кэш масштабированных иконок под размеры ячеек.
        self._ship_icon_scaled_cache = {}

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
        scaled_w = max(1, int(src_w * scale))
        scaled_h = max(1, int(src_h * scale))
        scaled = pygame.transform.smoothscale(source, (scaled_w, scaled_h))
        self._ship_icon_scaled_cache[cache_key] = scaled
        return scaled

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
        screen.blit(
            battle_scaled,
            (
                battle_x - battle_scaled.get_width() // 2,
                battle_y - battle_scaled.get_height() // 2,
            ),
        )
