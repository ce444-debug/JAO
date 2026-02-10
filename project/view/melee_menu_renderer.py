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

# [2026-02-03] CHANGE: якоря зон UQM в виртуальных координатах 320x240.
# Причина: визуальная проекция активных элементов menu.py в renderer.
UQM_ANCHORS = {
    "BATTLE": pygame.Rect(248, 112, 64, 48),
}

# [2026-02-03] CHANGE: индекс кнопки Battle в существующем правом списке.
# Причина: подсветка должна включаться только при активном Battle.
BATTLE_RIGHT_INDEX = 3


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
        # [2026-02-03] CHANGE: шрифт для версии renderer.
        # Причина: показать видимую метку активности рендера поверх UQM.
        self.version_font = pygame.font.SysFont("Arial", 20)
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

        # [2026-02-03] CHANGE: визуальная подсветка зоны Battle по якорю UQM.
        # Причина: активная кнопка Battle должна подсвечиваться в графике UQM.
        if getattr(menu, "selected_right", -1) == BATTLE_RIGHT_INDEX:
            battle_rect = UQM_ANCHORS["BATTLE"]
            battle_overlay = pygame.Surface((battle_rect.width, battle_rect.height), pygame.SRCALPHA)
            battle_overlay.fill((255, 255, 0, 70))
            self.virtual_surface.blit(battle_overlay, battle_rect.topleft)
            pygame.draw.rect(self.virtual_surface, (255, 255, 0), battle_rect, 2)

        scaled = pygame.transform.smoothscale(
            self.virtual_surface, (SCALED_W, SCALED_H)
        )

        # [2026-02-03] CHANGE: масштабированный кадр на весь экран 800x600.
        # Причина: UQM фон должен занимать весь экран без смещений.
        menu.screen.blit(scaled, (0, 0))

        # [2026-02-03] CHANGE: версия renderer поверх UQM-фона.
        # Причина: нужно видеть, что renderer активен, без влияния на логику.
        version_text = "UQM MENU v0.1 (renderer active)"
        text_surface = self.version_font.render(version_text, True, (255, 255, 0))
        menu.screen.blit(text_surface, (12, SCALED_H - text_surface.get_height() - 12))
