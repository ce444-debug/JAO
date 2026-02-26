# view/melee_menu_renderer.py
# [2026-02-03] reason: sprite-based control rendering via UQM frames 000..008 on virtual 320x240 surface.

import os
import pygame


# [2026-02-03] reason: fixed virtual/real pipeline for UQM menu assets.
VIRTUAL_SIZE = (320, 240)
REAL_SIZE = (800, 600)

# [2026-02-03] reason: control option order must match menu logic values.
CONTROL_OPTIONS = [
    "Human Control",
    "Weak Cyborg",
    "Good Cyborg",
    "Awesome Cyborg",
]


class MeleeMenuRenderer:
    def __init__(self):
        # [2026-02-03] reason: all rendering is done on virtual surface before scaling to real size.
        self.offscreen_surface = pygame.Surface(VIRTUAL_SIZE)

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
            return pygame.image.load(path).convert()
        fallback = pygame.Surface(VIRTUAL_SIZE, pygame.SRCALPHA)
        fallback.fill((0, 0, 0, 0))
        return fallback

    def draw_background(self, screen, frame_index):
        # [2026-02-03] reason: compatibility API keeps external calls stable.
        self.draw_main_menu(type("MenuProxy", (), {
            "screen": screen,
            "selected_right": -1,
            "settings": {
                "Team 1": {"control": "Human Control"},
                "Team 2": {"control": "Human Control"},
            },
        })())

    def draw_main_menu(self, menu):
        # [2026-02-03] reason: render background + control sprites using menu state without changing logic.
        self.offscreen_surface.fill((0, 0, 0))

        # background sprite 000
        self.offscreen_surface.blit(self.ui_sprites[0], (0, 0))

        # Team 1 control sprite at (224, 48)
        team1_idx = CONTROL_OPTIONS.index(menu.settings["Team 1"]["control"])
        if menu.selected_right == 0:
            team1_sprite = 1 + team1_idx
        else:
            team1_sprite = 5 + team1_idx
        self.offscreen_surface.blit(self.ui_sprites[team1_sprite], (224, 48))

        # Team 2 control sprite at (224, 168)
        team2_idx = CONTROL_OPTIONS.index(menu.settings["Team 2"]["control"])
        if menu.selected_right == 6:
            team2_sprite = 1 + team2_idx
        else:
            team2_sprite = 5 + team2_idx
        self.offscreen_surface.blit(self.ui_sprites[team2_sprite], (224, 168))

        scaled_surface = pygame.transform.scale(self.offscreen_surface, REAL_SIZE)
        menu.screen.blit(scaled_surface, (0, 0))
