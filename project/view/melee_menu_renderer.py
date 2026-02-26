# view/melee_menu_renderer.py
# [2026-02-03] reason: sprite-based control rendering via UQM frames 000..008 directly on menu.screen.

import os
import pygame
from project.config import SCREEN_W, SCREEN_H


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
        # [2026-02-03] reason: render directly to menu.screen using full-screen background scaling.
        screen = menu.screen

        bg = self.ui_sprites[0]
        bg_scaled = pygame.transform.scale(bg, (SCREEN_W, SCREEN_H))
        screen.blit(bg_scaled, (0, 0))

        # [2026-02-03] reason: compute control anchor positions proportionally to screen size.
        right_panel_x = int(SCREEN_W * 0.7)
        team1_y = int(SCREEN_H * 0.25)
        team2_y = int(SCREEN_H * 0.65)

        # Team 1 control sprite
        team1_idx = CONTROL_OPTIONS.index(menu.settings["Team 1"]["control"])
        if menu.selected_right == 0:
            team1_sprite = 1 + team1_idx
        else:
            team1_sprite = 5 + team1_idx
        screen.blit(self.ui_sprites[team1_sprite], (right_panel_x, team1_y))

        # Team 2 control sprite
        team2_idx = CONTROL_OPTIONS.index(menu.settings["Team 2"]["control"])
        if menu.selected_right == 6:
            team2_sprite = 1 + team2_idx
        else:
            team2_sprite = 5 + team2_idx
        screen.blit(self.ui_sprites[team2_sprite], (right_panel_x, team2_y))
