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
from project.config import GAME_SCREEN_W


class MeleeMenuRenderer:
    def __init__(self):
        self.frames = []
        self.frame_sizes = []
        self._last_frame_index = 0
        self._last_scale = None
        self._scaled_frames = []
        self._load_frames()

    def _load_frames(self):
        base_dir = os.path.join("assets", "ui", "menu")
        if not os.path.isdir(base_dir):
            print(f"[MeleeMenuRenderer] NOT FOUND: {base_dir}")
            return

        files = sorted(
            name for name in os.listdir(base_dir)
            if name.startswith("meleemenu-") and name.endswith(".png")
        )
        if not files:
            print(f"[MeleeMenuRenderer] NO FRAMES in: {base_dir}")
            return

        for name in files:
            path = os.path.join(base_dir, name)
            img = pygame.image.load(path).convert()
            self.frames.append(img)
            self.frame_sizes.append(img.get_size())

    def draw_main_menu(self, menu):
        if not self.frames:
            menu.draw_main_menu()
            return

        screen_h = menu.screen.get_height()
        screen_w = menu.screen.get_width()

        # 1) фон из кадров (анимированный)
        frame = self._get_scaled_frame(screen_h)
        if frame is not None:
            target_w = frame.get_width()
            x = (GAME_SCREEN_W - target_w) // 2

            clip_rect = pygame.Rect(0, 0, GAME_SCREEN_W, screen_h)
            menu.screen.set_clip(clip_rect)
            menu.screen.blit(frame, (x, 0))
            menu.screen.set_clip(None)

        # 2) поверх — обычная логика рендера меню (без заливки фона)
        menu.draw_main_menu(with_background=False)

        # 3) затемнение правой панели, если экран шире ожидаемого
        if screen_w > GAME_SCREEN_W:
            right_rect = pygame.Rect(GAME_SCREEN_W, 0, screen_w - GAME_SCREEN_W, screen_h)
            shade = pygame.Surface((right_rect.width, right_rect.height))
            shade.fill((0, 0, 0))
            shade.set_alpha(60)
            menu.screen.blit(shade, right_rect)

    def _get_scaled_frame(self, screen_h):
        if not self.frames:
            return None

        index = (pygame.time.get_ticks() // 120) % len(self.frames)
        if self._last_scale != screen_h:
            self._scaled_frames = []
            self._last_scale = screen_h

        if self._scaled_frames:
            return self._scaled_frames[index]

        self._scaled_frames = []
        for img, (img_w, img_h) in zip(self.frames, self.frame_sizes):
            scale = screen_h / img_h
            target_h = screen_h
            target_w = int(img_w * scale)
            scaled = pygame.transform.smoothscale(img, (target_w, target_h))
            self._scaled_frames.append(scaled)

        return self._scaled_frames[index]
