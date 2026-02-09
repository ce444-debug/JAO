# view/melee_menu_renderer.py
# [2026-02-03]
# FIX: стабильный полупрозрачный Super-Melee фон
# Причина:
# - menu.py делает fill(BLACK) каждый кадр
# - значит фон можно рисовать ТОЛЬКО ПОСЛЕ draw_main_menu()
#
# Это диагностический, но СТАБИЛЬНЫЙ режим.

import os
import pygame

# [2026-02-03] CHANGE: виртуальный экран 320x240 с масштабированием до окна.
# Причина: требуется масштаб-пайплайн для UQM PNG без смешивания координат.
VIRTUAL_W = 320
VIRTUAL_H = 240
SCALED_W = 800
SCALED_H = 600


class MeleeMenuRenderer:
    def __init__(self):
        self.image = None
        self.img_w = 0
        self.img_h = 0
        # [2026-02-03] CHANGE: отдельный виртуальный экран для UQM-рендера.
        # Причина: UQM PNG должны рисоваться в 320x240 и масштабироваться целиком.
        self.virtual_surface = pygame.Surface((VIRTUAL_W, VIRTUAL_H))
        # [2026-02-03] CHANGE: стартовый кадр инициализации.
        # Причина: renderer должен уметь принимать номер кадра.
        self.frame_index = 0
        self._load(self.frame_index)

    def _load(self, frame_index):
        # [2026-02-03] CHANGE: путь строится по номеру кадра.
        # Причина: renderer должен рисовать строго заданный кадр.
        path = os.path.join(
            "assets", "ui", "menu", f"meleemenu-{frame_index:03d}.png"
        )
        if not os.path.exists(path):
            print(f"[MeleeMenuRenderer] NOT FOUND: {path}")
            return

        img = pygame.image.load(path).convert()
        self.image = img
        self.img_w, self.img_h = img.get_size()

    def draw_main_menu(self, menu, frame_index=0):
        # [2026-02-03] CHANGE: renderer принимает номер кадра и рисует только его.
        # Причина: логика меню остаётся в menu.py, рендерер только рисует кадр.
        if frame_index != self.frame_index:
            self.frame_index = frame_index
            self._load(self.frame_index)

        if not self.image:
            return

        # [2026-02-03] CHANGE: рисуем UQM кадр в виртуальный экран 320x240.
        # Причина: единый масштаб-пайплайн для дальнейшего апскейла до окна.
        self.virtual_surface.fill((0, 0, 0))
        self.virtual_surface.blit(self.image, (0, 0))

        scaled = pygame.transform.smoothscale(
            self.virtual_surface, (SCALED_W, SCALED_H)
        )

        # [2026-02-03] CHANGE: масштабированный кадр на весь экран 800x600.
        # Причина: UQM фон должен занимать весь экран без смещений.
        menu.screen.blit(scaled, (0, 0))
