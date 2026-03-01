# view/melee_menu_renderer.py
# [2026-02-03] reason: sprite-based control rendering with anchor-based scaling from 320x240 layout.

import os
import pygame
from project.config import SCREEN_W, SCREEN_H


DEBUG_GRID = True
AUTO_ANCHOR_MODE = True

# [2026-02-03] reason: base UQM menu resolution for anchor conversion.
BASE_W = 320
BASE_H = 240
TEAM1_POS = (289, 39)
TEAM2_POS = (289, 182)
# [2026-02-03] reason: anchors for Save/Load/Battle button sprites in 320x240 layout space.
SAVE_T1_POS = (110, 205)
LOAD_T1_POS = (110, 225)
SAVE_T2_POS = (200, 205)
LOAD_T2_POS = (200, 225)
BATTLE_POS = (260, 210)

# [2026-02-03] reason: control option order must match menu logic values.
CONTROL_OPTIONS = [
    "Human Control",
    "Weak Cyborg",
    "Good Cyborg",
    "Awesome Cyborg",
]


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

            screen.blit(font.render(msg, True, (255,255,0)), (20, 20))

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
