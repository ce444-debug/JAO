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
        for frame in range(0, 9):
            self.ui_sprites[frame] = self._load_frame(frame)
        # [2026-02-03] reason: diagnostic click-capture flow for automatic anchor picking.
        self._anchor_step = 0  # 0 = waiting Team1, 1 = waiting Team2, 2 = done
        self._team1_temp = TEAM1_POS
        self._team2_temp = TEAM2_POS

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
            # [2026-02-03] reason: capture anchor centers from mouse clicks in runtime.
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    base_x = int(mx / scale_x)
                    base_y = int(my / scale_y)

                    if self._anchor_step == 0:
                        print(f"TEAM1_POS = ({base_x}, {base_y})")
                        self._team1_temp = (base_x, base_y)
                        self._anchor_step = 1

                    elif self._anchor_step == 1:
                        print(f"TEAM2_POS = ({base_x}, {base_y})")
                        self._team2_temp = (base_x, base_y)
                        self._anchor_step = 2

                        with open("melee_anchor_result.txt", "w") as f:
                            f.write(f"TEAM1_POS = {self._team1_temp}\n")
                            f.write(f"TEAM2_POS = {self._team2_temp}\n")

                        print("Anchors saved to melee_anchor_result.txt")

            font = pygame.font.SysFont(None, 22)
            if self._anchor_step == 0:
                txt = "Click center of TEAM 1 control slot"
            elif self._anchor_step == 1:
                txt = "Click center of TEAM 2 control slot"
            else:
                txt = "Anchors captured. Disable AUTO_ANCHOR_MODE."

            screen.blit(font.render(txt, True, (255, 255, 0)), (20, 20))

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
