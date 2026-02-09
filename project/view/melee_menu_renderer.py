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


class MeleeMenuRenderer:
    def __init__(self):
        self.image = None
        self.img_w = 0
        self.img_h = 0
        # [2026-02-03] CHANGE: отдельный виртуальный экран для UQM-рендера.
        # Причина: UQM PNG должны рисоваться в 320x240 и масштабироваться целиком.
        self.virtual_surface = pygame.Surface((VIRTUAL_W, VIRTUAL_H))
        self._load()

    def _load(self):
        path = os.path.join("assets", "ui", "menu", "meleemenu-000.png")
        if not os.path.exists(path):
            print(f"[MeleeMenuRenderer] NOT FOUND: {path}")
            return

        img = pygame.image.load(path).convert()
        self.image = img
        self.img_w, self.img_h = img.get_size()

    def draw_main_menu(self, menu):
        # [2026-02-03] CHANGE: сначала рендерим UQM-фон, затем legacy меню.
        # Причина: фон не должен перекрывать интерактивные элементы меню.
        if self.image:
            # [2026-02-03] CHANGE: рисуем UQM кадр в виртуальный экран 320x240.
            # Причина: единый масштаб-пайплайн для дальнейшего апскейла до окна.
            self.virtual_surface.fill((0, 0, 0))
            self.virtual_surface.blit(self.image, (0, 0))

            screen_w, screen_h = menu.screen.get_size()
            scaled = pygame.transform.smoothscale(
                self.virtual_surface, (screen_w, screen_h)
            )

            # [2026-02-03] CHANGE: масштабированный кадр на весь экран.
            # Причина: UQM фон должен занимать 800x600 без смещений.
            menu.screen.blit(scaled, (0, 0))

        # 1) обычный рендер меню (НЕ ТРОГАЕМ)
        menu.draw_main_menu()
