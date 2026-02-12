# view/melee_menu_renderer.py
# [2026-02-03] CHANGE: UQM renderer через виртуальный экран 320x240.
# Причина: меню должно рисоваться только PNG-кадрами UQM без legacy overlay.

import os
import pygame

VIRTUAL_W = 320
VIRTUAL_H = 240
SCALED_W = 800
SCALED_H = 600


class MeleeMenuRenderer:
    def __init__(self):
        self.image = None
        self.frame_index = -1
        # [2026-02-03] CHANGE: виртуальный буфер UQM 320x240.
        # Причина: корректный scale-pipeline 320x240 -> 800x600.
        self.virtual_surface = pygame.Surface((VIRTUAL_W, VIRTUAL_H))

    def _load(self, frame_index):
        # [2026-02-03] CHANGE: загрузка точного UQM-кадра по номеру.
        # Причина: renderer не содержит меню-логики, только рисует переданный кадр.
        path = os.path.join("assets", "ui", "menu", f"meleemenu-{frame_index:03d}.png")
        if not os.path.exists(path):
            path = os.path.join("assets", "ui", "menu", "meleemenu-000.png")
        if not os.path.exists(path):
            self.image = None
            return
        self.image = pygame.image.load(path).convert()

    def draw_background(self, screen, frame_index):
        # [2026-02-03] CHANGE: основной API отрисовки фона UQM.
        # Причина: menu.py передаёт готовый frame_index, renderer только рисует.
        if frame_index != self.frame_index:
            self.frame_index = frame_index
            self._load(frame_index)

        if self.image is None:
            return

        self.virtual_surface.fill((0, 0, 0))
        self.virtual_surface.blit(self.image, (0, 0))

        scaled = pygame.transform.smoothscale(
            self.virtual_surface,
            (SCALED_W, SCALED_H),
        )
        screen.blit(scaled, (0, 0))

    def draw_main_menu(self, menu, frame_index=0):
        # [2026-02-03] CHANGE: совместимость с текущим вызовом меню.
        # Причина: безопасный переход к draw_background без смены логики.
        self.draw_background(menu.screen, frame_index)
