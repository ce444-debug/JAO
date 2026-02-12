# view/melee_menu_renderer.py
# [2026-02-03] reason: sprite-based UQM renderer for main menu with virtual 320x240 pipeline.

import os
import pygame


# [2026-02-03] reason: fixed virtual/real sizes for UQM asset scaling.
VIRTUAL_SIZE = (320, 240)
REAL_SIZE = (800, 600)


class ButtonSprite:
    # [2026-02-03] reason: dedicated sprite container for normal/selected button images.
    def __init__(self, normal_img, selected_img, x, y, menu_index):
        self.normal = normal_img
        self.selected = selected_img
        self.x = x
        self.y = y
        self.menu_index = menu_index
        self.rect = self.normal.get_rect(topleft=(x, y))

    def draw(self, surface, selected=False):
        if selected:
            surface.blit(self.selected, (self.x, self.y))
        else:
            surface.blit(self.normal, (self.x, self.y))


class MeleeMenuRenderer:
    def __init__(self):
        # [2026-02-03] reason: render all menu visuals on virtual surface before upscaling.
        self.offscreen_surface = pygame.Surface(VIRTUAL_SIZE)

        # [2026-02-03] reason: load UQM main menu background frame.
        self.background = self._load_image("meleemenu-000.png", convert_alpha=False)

        # [2026-02-03] reason: sprite buttons fixed in virtual coordinates and tied to menu.selected_right indices.
        self.buttons = [
            ButtonSprite(
                self._load_image("battle_normal.png"),
                self._load_image("battle_selected.png"),
                224,
                64,
                3,
            ),
            ButtonSprite(
                self._load_image("save_normal.png"),
                self._load_image("save_selected.png"),
                224,
                104,
                1,
            ),
            ButtonSprite(
                self._load_image("load_normal.png"),
                self._load_image("load_selected.png"),
                224,
                128,
                2,
            ),
            ButtonSprite(
                self._load_image("quit_normal.png"),
                self._load_image("quit_selected.png"),
                224,
                184,
                7,
            ),
        ]

    def _asset_path(self, name):
        return os.path.join("assets", "ui", "menu", name)

    def _load_image(self, name, convert_alpha=True):
        # [2026-02-03] reason: safe asset loading with transparent fallback to avoid breaking menu flow.
        path = self._asset_path(name)
        if os.path.exists(path):
            img = pygame.image.load(path)
            return img.convert_alpha() if convert_alpha else img.convert()

        fallback = pygame.Surface((1, 1), pygame.SRCALPHA)
        fallback.fill((0, 0, 0, 0))
        return fallback

    def draw_background(self, screen, frame_index):
        # [2026-02-03] reason: backward-compatible API kept for existing calls.
        self.offscreen_surface.fill((0, 0, 0))
        self.offscreen_surface.blit(self.background, (0, 0))
        scaled_surface = pygame.transform.scale(self.offscreen_surface, REAL_SIZE)
        screen.blit(scaled_surface, (0, 0))

    def draw_main_menu(self, menu):
        # [2026-02-03] reason: main menu rendering is fully sprite-based and independent from menu logic.
        self.offscreen_surface.fill((0, 0, 0))
        self.offscreen_surface.blit(self.background, (0, 0))

        for button in self.buttons:
            button.draw(self.offscreen_surface, selected=(menu.selected_right == button.menu_index))

        scaled_surface = pygame.transform.scale(self.offscreen_surface, REAL_SIZE)
        menu.screen.blit(scaled_surface, (0, 0))
