# view/melee_menu_renderer.py
# [2026-02-03] reason: renderer рисует главное меню без изменения логики menu.py.

import os
import pygame
from project.config import SCREEN_W, SCREEN_H, GAME_SCREEN_W, PANEL_WIDTH


WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
GRAY = (200, 200, 200)


class MeleeMenuRenderer:
    def __init__(self):
        # [2026-02-03] reason: базовый UQM фон для главного меню.
        self.background = self._load_image("meleemenu-000.png")

    def _asset_path(self, name):
        return os.path.join("assets", "ui", "menu", name)

    def _load_image(self, name):
        # [2026-02-03] reason: безопасная загрузка ассетов без падения меню.
        path = self._asset_path(name)
        if os.path.exists(path):
            return pygame.image.load(path).convert()
        return None

    def _get_button_height(self, action):
        # [2026-02-03] reason: высоты кнопок строго по ТЗ.
        if action == "control":
            return 60
        if action in ("save", "load"):
            return 30
        if action == "battle":
            return 80
        return 40

    def draw_background(self, screen, frame_index):
        # [2026-02-03] reason: совместимый API; frame_index не меняет логику отрисовки кнопок.
        self.draw_main_menu(type("MenuProxy", (), {
            "screen": screen,
            "font_title": pygame.font.SysFont("Arial", 48),
            "font_menu": pygame.font.SysFont("Arial", 36),
            "font_small": pygame.font.SysFont("Arial", 20),
            "right_options": [],
            "selected_right": -1,
            "settings": {"Team 1": {"control": ""}, "Team 2": {"control": ""}},
            "selected_slot": -1,
            "teams": {"Team 1": [], "Team 2": []},
            "selected_team": "Team 1",
        })())

    def draw_main_menu(self, menu):
        # [2026-02-03] reason: рендер фон+заголовок+правая панель по данным menu.py без изменения логики.
        if self.background is not None:
            bg = pygame.transform.scale(self.background, (SCREEN_W, SCREEN_H))
            menu.screen.blit(bg, (0, 0))
        else:
            menu.screen.fill((0, 0, 0))

        title = menu.font_title.render("Super Melee", True, YELLOW)
        menu.screen.blit(title, (20, 10))

        right_panel_x = GAME_SCREEN_W
        right_panel_width = PANEL_WIDTH
        right_panel_height = SCREEN_H
        right_rect = pygame.Rect(right_panel_x, 0, right_panel_width, right_panel_height)
        pygame.draw.rect(menu.screen, (20, 20, 20), right_rect)

        y = 120
        margin = 10
        button_x = right_panel_x + 10
        button_w = right_panel_width - 20

        for idx, (opt_text, action, team) in enumerate(menu.right_options):
            h = self._get_button_height(action)
            rect = pygame.Rect(button_x, y, button_w, h)

            if idx == menu.selected_right:
                border_color = YELLOW
                border_width = 3
                text_color = YELLOW
            else:
                border_color = GRAY
                border_width = 1
                text_color = WHITE

            pygame.draw.rect(menu.screen, border_color, rect, border_width)

            if action == "control" and team:
                text_value = menu.settings[team]["control"]
            elif idx == 3 and menu.selected_right == -1:
                if menu.selected_slot >= 0:
                    ship = menu.teams[menu.selected_team][menu.selected_slot]
                    text_value = ship if ship else "Empty slot"
                else:
                    text_value = "Battle!"
            else:
                text_value = opt_text

            font = menu.font_menu if action == "control" else menu.font_small
            text_surface = font.render(text_value, True, text_color)
            text_x = rect.x + (rect.width - text_surface.get_width()) // 2
            text_y = rect.y + (rect.height - text_surface.get_height()) // 2
            menu.screen.blit(text_surface, (text_x, text_y))

            y += h + margin
