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
from project.config import GAME_SCREEN_W, SCREEN_H


class MeleeMenuRenderer:
    def __init__(self):
        self.image = None
        self.img_w = 0
        self.img_h = 0
        self._load()

    def _load(self):
        path = os.path.join("assets", "ui", "menu", "meleemenu-000.png")
        if not os.path.exists(path):
            print(f"[MeleeMenuRenderer] NOT FOUND: {path}")
            return

        img = pygame.image.load(path).convert()
        self.image = img
        self.img_w, self.img_h = img.get_size()

    def _draw_editing_overlay(self, menu):
        if not menu.editing_team:
            return

        h_half = (SCREEN_H - 100) // 2 - 10
        panels = {
            "Team 1": pygame.Rect(10, 80, GAME_SCREEN_W - 20, h_half),
            "Team 2": pygame.Rect(10, 80 + h_half + 20, GAME_SCREEN_W - 20, h_half),
        }
        area = panels.get(menu.selected_team)
        if area is None:
            return

        pulse = 160 + ((pygame.time.get_ticks() // 180) % 2) * 60
        color = (255, pulse, 0)
        header_rect = pygame.Rect(area.x + 6, area.y + 6, area.width - 12, 52)
        pygame.draw.rect(menu.screen, color, header_rect, 3)

    def draw_main_menu(self, menu):
        # 1) обычный рендер меню (НЕ ТРОГАЕМ)
        menu.draw_main_menu()

        if self.image:
            screen_h = menu.screen.get_height()

            # масштаб по высоте
            scale = screen_h / self.img_h
            target_h = screen_h
            target_w = int(self.img_w * scale)

            scaled = pygame.transform.smoothscale(
                self.image, (target_w, target_h)
            )

            # центрируем ВНУТРИ GAME_SCREEN_W
            x = (GAME_SCREEN_W - target_w) // 2

            # ограничиваем область (чтобы не лезло на правую панель)
            clip_rect = pygame.Rect(0, 0, GAME_SCREEN_W, screen_h)
            menu.screen.set_clip(clip_rect)

            # ПОЛУПРОЗРАЧНЫЙ фон — СТАБИЛЬНО
            overlay = scaled.copy()
            overlay.set_alpha(120)  # ← тут можешь крутить (80–150)

            menu.screen.blit(overlay, (x, 0))

            # вернуть clip
            menu.screen.set_clip(None)

        self._draw_editing_overlay(menu)
