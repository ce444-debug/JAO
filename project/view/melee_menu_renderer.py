# view/melee_menu_renderer.py
# [2026-02-03] reason: sprite-based UQM main menu renderer with virtual 320x240 pipeline.

import os
import pygame


# [2026-02-03] reason: fixed virtual/real pipeline constants for UQM assets.
VIRTUAL_SIZE = (320, 240)
REAL_SIZE = (800, 600)
SCALE = 2.5


class ButtonSprite:
    # [2026-02-03] reason: reusable sprite wrapper for normal/selected button states.
    def __init__(self, normal_img, selected_img, x, y):
        self.normal = normal_img
        self.selected = selected_img
        self.x = x
        self.y = y
        self.rect = self.normal.get_rect(topleft=(x, y))

    def draw(self, surface, selected=False):
        if selected:
            surface.blit(self.selected, (self.x, self.y))
        else:
            surface.blit(self.normal, (self.x, self.y))


class MeleeMenuRenderer:
    def __init__(self):
        # [2026-02-03] reason: offscreen virtual surface for all menu rendering.
        self.offscreen_surface = pygame.Surface(VIRTUAL_SIZE)
        self.background = self._load_image("meleemenu-000.png")

        # [2026-02-03] reason: load button sprites and keep coordinates in virtual 320x240 space.
        self.buttons = {
            "battle": ButtonSprite(
                self._load_image("battle_normal.png"),
                self._load_image("battle_selected.png"),
                224,
                64,
            ),
            "save": ButtonSprite(
                self._load_image("save_normal.png"),
                self._load_image("save_selected.png"),
                224,
                104,
            ),
            "load": ButtonSprite(
                self._load_image("load_normal.png"),
                self._load_image("load_selected.png"),
                224,
                128,
            ),
            "quit": ButtonSprite(
                self._load_image("quit_normal.png"),
                self._load_image("quit_selected.png"),
                224,
                184,
            ),
        }

    def _asset_path(self, name):
        return os.path.join("assets", "ui", "menu", name)

    def _load_image(self, name):
        # [2026-02-03] reason: safe asset loading with transparent fallback to keep logic running.
        path = self._asset_path(name)
        if os.path.exists(path):
            return pygame.image.load(path).convert_alpha()
        fallback = pygame.Surface((1, 1), pygame.SRCALPHA)
        fallback.fill((0, 0, 0, 0))
        return fallback

    def _map_selected_button(self, menu):
        # [2026-02-03] reason: map existing menu selection to 4 UQM sprite buttons only.
        if menu.selected_right == 3:
            return "battle"
        if menu.selected_right in (1, 4):
            return "save"
        if menu.selected_right in (2, 5):
            return "load"
        if menu.selected_right == 7:
            return "quit"
        return None

    def draw_main_menu(self, menu):
        # [2026-02-03] reason: render full menu only on virtual surface then upscale to real screen.
        self.offscreen_surface.fill((0, 0, 0))
        self.offscreen_surface.blit(self.background, (0, 0))

        selected_button = self._map_selected_button(menu)

        self.buttons["battle"].draw(self.offscreen_surface, selected=(selected_button == "battle"))
        self.buttons["save"].draw(self.offscreen_surface, selected=(selected_button == "save"))
        self.buttons["load"].draw(self.offscreen_surface, selected=(selected_button == "load"))
        self.buttons["quit"].draw(self.offscreen_surface, selected=(selected_button == "quit"))

        scaled_surface = pygame.transform.scale(self.offscreen_surface, REAL_SIZE)
        menu.screen.blit(scaled_surface, (0, 0))

    def draw_background(self, screen, frame_index):
        # [2026-02-03] reason: backward-compatible API routed to the sprite-based main draw.
        self.offscreen_surface.fill((0, 0, 0))
        self.offscreen_surface.blit(self.background, (0, 0))
        scaled_surface = pygame.transform.scale(self.offscreen_surface, REAL_SIZE)
        screen.blit(scaled_surface, (0, 0))
