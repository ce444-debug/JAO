# title_screen.py
# 2025-12-10 — титульный экран VOID ENGINE
# 2025-12-10 — новая версия: полное изображение + атмосферный фон без чёрных полос
# Причина: постер должен полностью помещаться и быть органично обрамлён под любое разрешение.

import pygame
import numpy as np
from pygame.surfarray import array3d, make_surface
from typing import Tuple


def fast_blur(surface: pygame.Surface, radius: int = 12) -> pygame.Surface:
    """
    Очень быстрый псевдо-Gaussian blur через downscale-upscale.
    Делается в разы быстрее настоящего размытия.
    """
    if radius <= 0:
        return surface.copy()

    w, h = surface.get_size()
    scale = max(1, radius)

    small = pygame.transform.smoothscale(surface, (w // scale, h // scale))
    blurred = pygame.transform.smoothscale(small, (w, h))
    return blurred


class TitleScreen:
    def __init__(self, screen_size: Tuple[int, int], poster_path: str, build_label: str = ""):
        self.screen_width, self.screen_height = screen_size

        # Загрузим оригинальный постер
        self.poster = pygame.image.load(poster_path).convert()

        # Создадим фон (blur fill)
        self.bg_surface = self._create_background_fill()

        # Создадим версию постера, вписанную полностью (contain), но без обрезания
        self.poster_surface, self.poster_rect = self._create_contained_poster()

        # Шрифт
        self.font = pygame.font.SysFont("arial", 28)

        self.blink_timer = 0.0
        self.blink_period = 1.0
        self.show_press_any_key = True
        self.done = False
        self.build_label = build_label

    def _create_background_fill(self) -> pygame.Surface:
        """
        Размытый и затемнённый фон, который растягивается на весь экран.
        Сам постер будет поверх — полностью видимый.
        """
        # Берём постер, растягиваем на весь экран (можно деформировать)
        raw_fill = pygame.transform.smoothscale(self.poster, (self.screen_width, self.screen_height))

        # Размываем
        blurred = fast_blur(raw_fill, radius=16)

        # Затемняем фон на 20% для лучшей читаемости центрального постера
        dark_overlay = pygame.Surface((self.screen_width, self.screen_height))
        dark_overlay.fill((0, 0, 0))
        dark_overlay.set_alpha(80)

        blurred.blit(dark_overlay, (0, 0))
        return blurred

    def _create_contained_poster(self):
        """
        Масштабируем постер так, чтобы он целиком умещался (contain),
        а фон заполняет пространство вокруг — без чёрных полос.
        """
        pw, ph = self.poster.get_size()
        sw, sh = self.screen_width, self.screen_height

        scale = min(sw / pw, sh / ph)

        new_width = int(pw * scale)
        new_height = int(ph * scale)

        scaled = pygame.transform.smoothscale(self.poster, (new_width, new_height))

        rect = scaled.get_rect(center=(sw // 2, sh // 2))
        return scaled, rect

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            self.done = True
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.done = True

    def update(self, dt: float):
        self.blink_timer += dt
        if self.blink_timer >= self.blink_period:
            self.blink_timer -= self.blink_period
            self.show_press_any_key = not self.show_press_any_key

    def draw(self, surface: pygame.Surface):
        # 1. Фон — растянутый, размытый постер
        surface.blit(self.bg_surface, (0, 0))

        # 2. Постер целиком (contain)
        surface.blit(self.poster_surface, self.poster_rect)

        # 3. Текст
        if self.show_press_any_key:
            text = "Press any key to start"
            txt = self.font.render(text, True, (230, 230, 240))
            shadow = self.font.render(text, True, (0, 0, 0))

            txt_rect = txt.get_rect(midbottom=(self.screen_width // 2, self.screen_height - 40))
            shadow_rect = txt_rect.copy()
            shadow_rect.move_ip(2, 2)

            surface.blit(shadow, shadow_rect)
            surface.blit(txt, txt_rect)

        if self.build_label:
            build_txt = self.font.render(self.build_label, True, (170, 170, 180))
            build_rect = build_txt.get_rect(topleft=(20, 16))
            surface.blit(build_txt, build_rect)
