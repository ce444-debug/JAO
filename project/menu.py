# menu.py
# [2026-02-03] Минимальный рефакторинг без ломки:
# - добавлен MeleeMenuRenderer (view/melee_menu_renderer.py)
# - отрисовка main_menu теперь идёт через renderer (если доступен)
# Причина: вынести графику из menu.py поэтапно и перейти на UQM PNG, сохранив текущую логику.

import pygame
import sys
import json
import random
from project.ships.registry import SHIP_CLASSES
from project.config import SCREEN_W, SCREEN_H, PANEL_WIDTH, GAME_SCREEN_W

# [2026-02-03] Безопасный импорт renderer (не ломаем запуск, даже если папка view не package).
# Причина: избежать ModuleNotFoundError / ImportError при разной структуре PYTHONPATH.
try:
    from view.melee_menu_renderer import MeleeMenuRenderer
except Exception:
    MeleeMenuRenderer = None

# ---------- Colors & constants ----------
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
GRAY = (200, 200, 200)
BLACK = (0, 0, 0)

SAVES_FILE = "saved_teams.json"
CONTROL_OPTIONS = ["Human Control", "Weak Cyborg", "Good Cyborg", "Awesome Cyborg"]
LEFT_PANEL_COLS = 7

# [2026-02-03] CHANGE: табличное соответствие логического состояния и UQM-кадра.
# Причина: кадры UQM выбираются по смыслу активного пункта, а не по индексу/счётчику.
FRAME_MAP = {
    ("right", "none"): 0,
    ("right", "battle"): 26,
    ("right", "save_top"): 23,
    ("right", "load_top"): 24,
    ("right", "save_bottom"): 19,
    ("right", "load_bottom"): 20,
    ("right", "control_top"): 5,
    ("right", "control_bottom"): 13,
}

# In-memory cache for last menu state
_CACHED_CONFIG = None

class SuperMeleeMenu:
    def __init__(self, screen, clock):
        self.screen = screen
        self.clock = clock

        # Fonts
        self.font_title = pygame.font.SysFont("Arial", 48)
        self.font_menu = pygame.font.SysFont("Arial", 36)
        self.font_small = pygame.font.SysFont("Arial", 20)

        # [2026-02-03] Renderer для поэтапного переноса отрисовки.
        # Причина: оставить логику меню в menu.py, а графику постепенно увести в view/.
        self.renderer = MeleeMenuRenderer() if MeleeMenuRenderer is not None else None
        # [2026-02-03] CHANGE: текущий кадр меню для UQM-отрисовки.
        # Причина: привязать существующую логику выбора к графическому кадру.
        self.current_frame = 0

        # FSM state
        self.state = "main_menu"

        # Team data
        self.team_slots = 14
        self.teams = {"Team 1": [None] * self.team_slots,
                      "Team 2": [None] * self.team_slots}
        self.team_names = {"Team 1": "Team 1", "Team 2": "Team 2"}
        self.settings = {"Team 1": {"control": "Human Control"},
                         "Team 2": {"control": "Good Cyborg"}}

        # Menu cursor/selection
        self.selected_right = 3  # Start on "Battle!"
        self.selected_team = "Team 1"
        self.selected_slot = -1  # -1 = team header
        self.last_upper_slot = 0

        # Right panel options: (display_text, action, team)
        self.right_options = [
            ("Team 1 Control", "control", "Team 1"),
            ("Save", "save", "Team 1"),
            ("Load", "load", "Team 1"),
            ("Battle!", "battle", None),
            ("Save", "save", "Team 2"),
            ("Load", "load", "Team 2"),
            ("Team 2 Control", "control", "Team 2"),
            ("Quit", "quit", None)
        ]

        # Aux variables
        self.ship_list = list(SHIP_CLASSES.keys()) + ["?"]
        self.selected_ship_index = 0
        self.editing_team = False
        self.editing_team_name = ""
        self.initial_ships = {"Team 1": None, "Team 2": None}
        self.initial_slots = {'Team 1': None, 'Team 2': None}  # [25-05-2025]

        # Load cached or saved config
        global _CACHED_CONFIG
        if _CACHED_CONFIG is not None:
            self._apply_loaded_config(_CACHED_CONFIG)
        else:
            try:
                with open(SAVES_FILE, "r") as f:
                    saves = json.load(f)
                if saves and "last_config" in saves:
                    self._apply_loaded_config(saves["last_config"])
                    _CACHED_CONFIG = saves["last_config"]
            except Exception:
                pass
        self.normalize_teams()

    def _apply_loaded_config(self, cfg):
        self.teams = cfg.get("teams", self.teams)
        self.team_names = cfg.get("team_names", self.team_names)
        self.settings = cfg.get("settings", self.settings)
        for team in ["Team 1", "Team 2"]:
            ctrl = self.settings[team]["control"]
            if ctrl not in CONTROL_OPTIONS:
                self.settings[team]["control"] = "Good Cyborg" if "cyborg" in ctrl.lower() else "Human Control"

    def normalize_teams(self):
        for team in self.teams:
            while len(self.teams[team]) < self.team_slots:
                self.teams[team].append(None)
            if len(self.teams[team]) > self.team_slots:
                self.teams[team] = self.teams[team][:self.team_slots]
            self.teams[team] = [ship if ship in SHIP_CLASSES else None for ship in self.teams[team]]

    def is_ship_available(self, team, ship_name, slot):
        available_ships = [(i, ship) for i, ship in enumerate(self.teams[team]) if ship == ship_name and self.teams[team][i] != "eliminated"]
        if not available_ships:
            return False
        return slot in [i for i, _ in available_ships]

    def get_opposite_slot(self, slot):
        if slot < 0:
            return 0
        return slot + LEFT_PANEL_COLS if slot < LEFT_PANEL_COLS else slot - LEFT_PANEL_COLS

    def display(self):
        self.reset()
        while True:
            if self.state == "main_menu":
                # [2026-02-03] CHANGE: выбор кадра только через таблицу соответствий FRAME_MAP.
                # Причина: кадр UQM определяется смыслом активного пункта, не индексом.
                frame_state = ("right", "none")
                if self.selected_right >= 0:
                    _opt_text, action, team = self.right_options[self.selected_right]
                    if action == "battle":
                        frame_state = ("right", "battle")
                    elif action == "save" and team == "Team 1":
                        frame_state = ("right", "save_top")
                    elif action == "load" and team == "Team 1":
                        frame_state = ("right", "load_top")
                    elif action == "save" and team == "Team 2":
                        frame_state = ("right", "save_bottom")
                    elif action == "load" and team == "Team 2":
                        frame_state = ("right", "load_bottom")
                    elif action == "control" and team == "Team 1":
                        frame_state = ("right", "control_top")
                    elif action == "control" and team == "Team 2":
                        frame_state = ("right", "control_bottom")
                self.current_frame = FRAME_MAP.get(frame_state, 0)
                # [2026-02-03] main_menu теперь рисуется через renderer, если он доступен.
                # Причина: перенос отрисовки из menu.py в view/ без ломки логики.
                if self.renderer is not None:
                    # [2026-02-03] CHANGE: main menu рисуется только через UQM renderer.
                    # Причина: убрать legacy draw и использовать UQM PNG кадры.
                    self.renderer.draw_background(self.screen, self.current_frame)
                else:
                    self.draw_main_menu()
                self.handle_main_events()
            elif self.state == "ship_select":
                self.draw_ship_select()
                self.handle_ship_select_events()
            elif self.state == "battle_select":
                cfg = self.battle_select_mode()
                if cfg:
                    return cfg
            elif self.state == "exit":
                return None
            pygame.display.flip()
            self.clock.tick(30)

    def draw_main_menu(self):
        # [2026-02-03] CHANGE: legacy main menu draw отключён.
        # Причина: основной экран меню полностью рисуется через UQM renderer.
        pass

    def draw_team_panel(self, team, area):
        name = self.team_names[team]
        if self.selected_right == -1 and self.selected_team == team and self.selected_slot == -1 and self.editing_team:
            surf = self.font_menu.render(self.editing_team_name, True, YELLOW)
        else:
            surf = self.font_menu.render(name, True, WHITE)
        self.screen.blit(surf, (area.x + 10, area.y + 10))
        if self.selected_right == -1 and self.selected_team == team and self.selected_slot == -1:
            pygame.draw.rect(self.screen, YELLOW,
                             (area.x + 8, area.y + 8, surf.get_width() + 4, surf.get_height() + 4), 1)
        slot_m = 5
        cols = LEFT_PANEL_COLS
        slot_w = (area.width - 20 - (cols - 1) * slot_m) // cols
        slot_h = 40
        start_y = area.y + 60
        points = 0
        for i in range(self.team_slots):
            row = i // cols
            col = i % cols
            r = pygame.Rect(area.x + 10 + col * (slot_w + slot_m),
                            start_y + row * (slot_h + slot_m), slot_w, slot_h)
            pygame.draw.rect(self.screen, GRAY, r, 1)
            txt = self.teams[team][i] if self.teams[team][i] else "---"
            if self.selected_right == -1 and self.selected_team == team and self.selected_slot == i:
                pygame.draw.rect(self.screen, YELLOW, r, 2)
            self.screen.blit(self.font_small.render(txt, True, WHITE), (r.x + 5, r.y + 10))
            if txt != "---" and txt in SHIP_CLASSES:
                try:
                    dummy = SHIP_CLASSES[txt](0, 0, WHITE)
                    points += getattr(dummy, "cost", 0)
                except:
                    pass
        self.screen.blit(self.font_small.render(f"Points: {points}", True, WHITE),
                         (area.x + 10, area.bottom - 30))

    def draw_right_panel(self, area):
        pygame.draw.rect(self.screen, (40, 40, 40), area)
        y = 50
        margin = 10
        for idx, (opt_text, action, team) in enumerate(self.right_options):
            if action == "battle":
                h = 80
            elif action == "control":
                h = 60
            elif action == "save" or action == "load":
                h = 30
            else:  # quit
                h = 40
            font = self.font_menu if action == "control" else self.font_small
            if idx == 3 and self.selected_right == -1:
                if self.selected_slot >= 0:
                    ship = self.teams[self.selected_team][self.selected_slot]
                    txt = ship if ship else "Empty slot"
                else:
                    txt = "Battle!"
            elif action == "control" and team:
                txt = self.settings[team]["control"]
            else:
                txt = opt_text
            if action == "quit":
                y += 20
            border_color = YELLOW if idx == self.selected_right else GRAY
            border_width = 2 if idx == self.selected_right else 1
            r = pygame.Rect(area.x + margin, y, area.width - 2 * margin, h)
            pygame.draw.rect(self.screen, border_color, r, border_width)
            surf = font.render(txt, True, WHITE)
            text_x = r.x + (r.width - surf.get_width()) // 2
            text_y = r.y + (r.height - surf.get_height()) // 2
            self.screen.blit(surf, (text_x, text_y))
            y += h + margin

    def draw_ship_select(self):
        self.screen.fill((20, 20, 60))
        self.screen.blit(self.font_title.render("Select Ship", True, YELLOW),
                         (SCREEN_W // 2 - 100, 20))
        self.screen.blit(self.font_small.render("Use arrows, Enter to select", True, WHITE),
                         (50, SCREEN_H - 40))
        list_x = SCREEN_W // 2 - 100
        list_y = 100
        for i, name in enumerate(self.ship_list):
            col = YELLOW if i == self.selected_ship_index else GRAY
            self.screen.blit(self.font_menu.render(name, True, col), (list_x, list_y + i * 40))

    def handle_main_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.save_last_config()
                pygame.quit()
                sys.exit()
            elif ev.type == pygame.KEYDOWN:
                if self.editing_team:
                    if ev.key == pygame.K_RETURN:
                        self.team_names[self.selected_team] = self.editing_team_name
                        self.editing_team = False
                    elif ev.key == pygame.K_BACKSPACE:
                        self.editing_team_name = self.editing_team_name[:-1]
                    else:
                        self.editing_team_name += ev.unicode
                    return
                if self.selected_right == -1:
                    if ev.key == pygame.K_UP:
                        if self.selected_slot == -1:
                            if self.selected_team == "Team 2":
                                self.selected_team = "Team 1"
                                self.selected_slot = self.get_opposite_slot(self.last_upper_slot)
                        else:
                            new_slot = self.selected_slot - LEFT_PANEL_COLS
                            self.selected_slot = -1 if new_slot < -1 else new_slot
                    elif ev.key == pygame.K_DOWN:
                        if self.selected_slot == -1:
                            self.selected_slot = 0
                        else:
                            new_slot = self.selected_slot + LEFT_PANEL_COLS
                            if new_slot >= self.team_slots:
                                if self.selected_team == "Team 1":
                                    self.last_upper_slot = self.selected_slot
                                    self.selected_team = "Team 2"
                                    self.selected_slot = -1
                            else:
                                self.selected_slot = new_slot
                    elif ev.key == pygame.K_LEFT:
                        if self.selected_slot > -1 and self.selected_slot % LEFT_PANEL_COLS > 0:
                            self.selected_slot -= 1
                    elif ev.key == pygame.K_RIGHT:
                        if self.selected_slot == -1:
                            self.selected_slot = 0
                        else:
                            col = self.selected_slot % LEFT_PANEL_COLS
                            if col < LEFT_PANEL_COLS - 1 and self.selected_slot < self.team_slots - 1:
                                self.selected_slot += 1
                            else:
                                self.selected_right = 3
                    elif ev.key == pygame.K_RETURN:
                        if self.selected_slot == -1:
                            self.editing_team = True
                            self.editing_team_name = self.team_names[self.selected_team]
                        else:
                            self.state = "ship_select"
                            self.selected_ship_index = 0
                    elif ev.key == pygame.K_DELETE and self.selected_slot >= 0:
                        self.teams[self.selected_team][self.selected_slot] = None
                    elif ev.key == pygame.K_TAB:
                        self.selected_team = "Team 2" if self.selected_team == "Team 1" else "Team 1"
                else:
                    if ev.key == pygame.K_LEFT:
                        current_right = self.selected_right
                        self.selected_right = -1
                        self.selected_team = "Team 1" if current_right <= 3 else "Team 2"
                        self.selected_slot = self.team_slots - 1
                    elif ev.key == pygame.K_UP:
                        self.selected_right = max(0, self.selected_right - 1)
                    elif ev.key == pygame.K_DOWN:
                        self.selected_right = min(len(self.right_options) - 1, self.selected_right + 1)
                    elif ev.key == pygame.K_RETURN:
                        self.activate_right_option()
                    elif ev.key == pygame.K_TAB:
                        self.selected_team = "Team 2" if self.selected_team == "Team 1" else "Team 1"

    def activate_right_option(self):
        opt_text, action, team = self.right_options[self.selected_right]
        if action == "battle":
            self.state = "battle_select"
        elif action == "quit":
            self.save_last_config()
            pygame.quit()
            sys.exit()
        elif action == "control" and team:
            cur = self.settings[team]["control"]
            idx = CONTROL_OPTIONS.index(cur)
            self.settings[team]["control"] = CONTROL_OPTIONS[(idx + 1) % len(CONTROL_OPTIONS)]
        elif action == "save" and team:
            self.universal_save(team)
        elif action == "load" and team:
            self.universal_load(team)

    def handle_ship_select_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.save_last_config()
                pygame.quit()
                sys.exit()
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_UP:
                    self.selected_ship_index = max(0, self.selected_ship_index - 1)
                elif ev.key == pygame.K_DOWN:
                    self.selected_ship_index = min(len(self.ship_list) - 1, self.selected_ship_index + 1)
                elif ev.key == pygame.K_RETURN:
                    chosen = self.ship_list[self.selected_ship_index]
                    if chosen == "?":
                        chosen = random.choice(list(SHIP_CLASSES.keys()))
                    self.teams[self.selected_team][self.selected_slot] = chosen
                    self.state = "main_menu"

    def draw_battle_select(self, sel1, sel2, conf1=None, conf2=None):
        self.screen.fill(BLACK)
        panel_h = (SCREEN_H - 100) // 2
        panel1 = pygame.Rect(10, 80, GAME_SCREEN_W - 20, panel_h)
        panel2 = pygame.Rect(10, panel1.bottom + 20, GAME_SCREEN_W - 20, panel_h)
        total = self.team_slots + 2
        cols = 4
        m = 5
        cell_w = (panel1.width - 20 - (cols - 1) * m) // cols
        cell_h = 40

        def draw_grid(team, panel, sel, confirmed_idx):
            for idx in range(total):
                r, c = divmod(idx, cols)
                x = panel.x + 10 + c * (cell_w + m)
                y = panel.y + 10 + r * (cell_h + m)
                rect = pygame.Rect(x, y, cell_w, cell_h)
                if isinstance(confirmed_idx, int) and idx == confirmed_idx:
                    border_color = GREEN
                    border_width = 3
                elif idx == sel:
                    border_color = YELLOW
                    border_width = 2
                else:
                    border_color = GRAY
                    border_width = 1
                pygame.draw.rect(self.screen, border_color, rect, border_width)
                if idx < self.team_slots:
                    txt = self.teams[team][idx] if self.teams[team][idx] else "---"
                elif idx == self.team_slots:
                    txt = "?"
                else:
                    txt = "X"
                self.screen.blit(self.font_small.render(str(txt), True, WHITE),
                                 (rect.x + 5, rect.y + 10))

        draw_grid("Team 1", panel1, sel1, conf1)
        draw_grid("Team 2", panel2, sel2, conf2)

        instr = "Team1: E/D/S/F + A to confirm; Team2: Arrows + RCTRL to confirm"
        self.screen.blit(self.font_small.render(instr, True, WHITE), (10, SCREEN_H - 30))

    def battle_select_mode(self):
        max_index = self.team_slots + 1
        battle_sel = {"Team 1": 0, "Team 2": 0}
        confirm_idx = {"Team 1": None, "Team 2": None}

        if self.settings["Team 1"]["control"] != "Human Control":
            battle_sel["Team 1"] = self.team_slots
            confirm_idx["Team 1"] = self.team_slots
        if self.settings["Team 2"]["control"] != "Human Control":
            battle_sel["Team 2"] = self.team_slots
            confirm_idx["Team 2"] = self.team_slots

        clock = pygame.time.Clock()
        while confirm_idx["Team 1"] is None or confirm_idx["Team 2"] is None:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.save_last_config()
                    pygame.quit()
                    sys.exit()
                if ev.type == pygame.KEYDOWN:
                    if self.settings["Team 1"]["control"] == "Human Control":
                        if ev.key == pygame.K_e and battle_sel["Team 1"] - 4 >= 0:
                            battle_sel["Team 1"] -= 4
                        elif ev.key == pygame.K_d and battle_sel["Team 1"] + 4 <= max_index:
                            battle_sel["Team 1"] += 4
                        elif ev.key == pygame.K_s and battle_sel["Team 1"] > 0:
                            battle_sel["Team 1"] -= 1
                        elif ev.key == pygame.K_f and battle_sel["Team 1"] < max_index:
                            battle_sel["Team 1"] += 1
                        elif ev.key == pygame.K_a:
                            if not (battle_sel["Team 1"] < self.team_slots and
                                    self.teams["Team 1"][battle_sel["Team 1"]] is None):
                                confirm_idx["Team 1"] = battle_sel["Team 1"]
                    if self.settings["Team 2"]["control"] == "Human Control":
                        if ev.key == pygame.K_LEFT and battle_sel["Team 2"] > 0:
                            battle_sel["Team 2"] -= 1
                        elif ev.key == pygame.K_RIGHT and battle_sel["Team 2"] < max_index:
                            battle_sel["Team 2"] += 1
                        elif ev.key == pygame.K_UP and battle_sel["Team 2"] - 4 >= 0:
                            battle_sel["Team 2"] -= 4
                        elif ev.key == pygame.K_DOWN and battle_sel["Team 2"] + 4 <= max_index:
                            battle_sel["Team 2"] += 4
                        elif ev.key == pygame.K_RCTRL:
                            if not (battle_sel["Team 2"] < self.team_slots and
                                    self.teams["Team 2"][battle_sel["Team 2"]] is None):
                                confirm_idx["Team 2"] = battle_sel["Team 2"]

            self.draw_battle_select(battle_sel["Team 1"],
                                    battle_sel["Team 2"],
                                    confirm_idx["Team 1"],
                                    confirm_idx["Team 2"])
            pygame.display.flip()
            clock.tick(30)

        sel1 = confirm_idx["Team 1"]
        sel2 = confirm_idx["Team 2"]

        if sel1 == self.team_slots + 1 or sel2 == self.team_slots + 1:
            self.reset()
            return self.generate_config()

        ship1 = self.teams["Team 1"][sel1] if sel1 < self.team_slots else "?"
        ship2 = self.teams["Team 2"][sel2] if sel2 < self.team_slots else "?"
        self.initial_ships = {"Team 1": ship1, "Team 2": ship2}
        self.initial_slots = {'Team 1': None, 'Team 2': None}  # [25-05-2025]

        cfg = {
            'mode': f"{self.settings['Team 1']['control']} vs {self.settings['Team 2']['control']}",
            'teams': self.teams,
            'team_names': self.team_names,
            'settings': self.settings,
            'initial_ships': self.initial_ships,
            'initial_slots': self.initial_slots,  # [25-05-2025]
        }
        self.save_last_config()
        return cfg

    def reset(self):
        self.state = "main_menu"
        self.selected_right = 3
        self.selected_slot = -1
        self.selected_team = "Team 1"

    def generate_config(self):
        for team in ["Team 1", "Team 2"]:
            ctrl = self.settings[team]["control"]
            diff = "Easy" if ctrl == "Weak Cyborg" else "Medium" if ctrl == "Good Cyborg" else "Hard" if ctrl == "Awesome Cyborg" else "N/A"
            self.settings[team]["cyborg_difficulty"] = diff

        if self.initial_ships["Team 1"] is None or self.initial_ships["Team 1"] == "?":
            available = [(i, ship) for i, ship in enumerate(self.teams["Team 1"]) if ship and ship != "eliminated"]
            self.initial_ships["Team 1"] = available[0][1] if available else "?"
            self.initial_slots = {'Team 1': None, 'Team 2': None}  # [25-05-2025]
        if self.initial_ships["Team 2"] is None or self.initial_ships["Team 2"] == "?":
            available = [(i, ship) for i, ship in enumerate(self.teams["Team 2"]) if ship and ship != "eliminated"]
            self.initial_ships["Team 2"] = available[0][1] if available else "?"
            self.initial_slots = {'Team 1': None, 'Team 2': None}  # [25-05-2025]

        return {
            'mode': f"{self.settings['Team 1']['control']} vs {self.settings['Team 2']['control']}",
            'teams': self.teams,
            'team_names': self.team_names,
            'settings': self.settings,
            'initial_ships': self.initial_ships,
            'initial_slots': getattr(self, 'initial_slots', {'Team 1': 0, 'Team 2': 0}),  # [25-05-2025]
        }

    def choose_save_option(self):
        options = ["New Save"]
        try:
            with open(SAVES_FILE, "r") as f:
                saves = json.load(f)
            options += list(saves.get("profiles", {}).keys())
        except Exception:
            pass
        idx = 0
        choosing = True
        while choosing:
            self.screen.fill(BLACK)
            self.screen.blit(self.font_title.render("Save Profile", True, YELLOW), (50, 20))
            for i, opt in enumerate(options):
                col = YELLOW if i == idx else GRAY
                self.screen.blit(self.font_menu.render(opt, True, col), (100, 100 + i * 50))
            pygame.display.flip()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.save_last_config()
                    pygame.quit()
                    sys.exit()
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_UP:
                        idx = max(0, idx - 1)
                    elif ev.key == pygame.K_DOWN:
                        idx = min(len(options) - 1, idx + 1)
                    elif ev.key == pygame.K_RETURN:
                        choosing = False
            self.clock.tick(30)
        return options[idx]

    def choose_profile(self):
        try:
            with open(SAVES_FILE, "r") as f:
                saves = json.load(f)
            profiles = list(saves.get("profiles", {}).keys())
        except Exception:
            profiles = []
        if not profiles:
            return None
        idx = 0
        choosing = True
        while choosing:
            self.screen.fill(BLACK)
            self.screen.blit(self.font_title.render("Load Profile", True, YELLOW), (50, 20))
            for i, opt in enumerate(profiles):
                col = YELLOW if i == idx else GRAY
                self.screen.blit(self.font_menu.render(opt, True, col), (100, 100 + i * 50))
            pygame.display.flip()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.save_last_config()
                    pygame.quit()
                    sys.exit()
                elif ev.type == pygame.K_UP:
                    idx = max(0, idx - 1)
                elif ev.key == pygame.K_DOWN:
                    idx = min(len(profiles) - 1, idx + 1)
                elif ev.key == pygame.K_RETURN:
                    choosing = False
            self.clock.tick(30)
        return profiles[idx]

    def prompt_for_save_name(self, prompt_msg):
        name = ""
        entering = True
        while entering:
            self.screen.fill(BLACK)
            self.screen.blit(self.font_menu.render(prompt_msg + name, True, WHITE), (50, SCREEN_H // 2))
            pygame.display.flip()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.save_last_config()
                    pygame.quit()
                    sys.exit()
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_RETURN:
                        entering = False
                    elif ev.key == pygame.K_BACKSPACE:
                        name = name[:-1]
                    else:
                        name += ev.unicode
            self.clock.tick(30)
        return name.strip()

    def prompt_confirm_overwrite(self, name):
        asking = True
        idx = 0
        options = ["Yes", "No"]
        while asking:
            self.screen.fill(BLACK)
            self.screen.blit(self.font_menu.render(f"Overwrite '{name}'?", True, WHITE), (50, 100))
            for i, opt in enumerate(options):
                col = YELLOW if i == idx else GRAY
                self.screen.blit(self.font_menu.render(opt, True, col), (100, 200 + i * 60))
            pygame.display.flip()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.save_last_config()
                    pygame.quit()
                    sys.exit()
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_UP:
                        idx = max(0, idx - 1)
                    elif ev.key == pygame.K_DOWN:
                        idx = min(1, idx + 1)
                    elif ev.key == pygame.K_RETURN:
                        asking = False
            self.clock.tick(30)
        return idx == 0

    def universal_save(self, team):
        option = self.choose_save_option()
        if option is None:
            return
        if option == "New Save":
            name = self.prompt_for_save_name("Enter new profile name: ")
            if not name:
                return
        else:
            name = option
            if not self.prompt_confirm_overwrite(name):
                return
        cfg = {"fleet": self.teams[team], "team_name": self.team_names[team]}
        try:
            with open(SAVES_FILE, "r") as f:
                saves = json.load(f)
        except Exception:
            saves = {}
        profiles = saves.get("profiles", {})
        profiles[name] = cfg
        saves["profiles"] = profiles
        try:
            with open(SAVES_FILE, "w") as f:
                json.dump(saves, f, indent=2)
        except Exception as e:
            print(f"Failed to save profile: {e}")

    def universal_load(self, team):
        profile = self.choose_profile()
        if not profile:
            return
        try:
            with open(SAVES_FILE, "r") as f:
                saves = json.load(f)
            conf = saves.get("profiles", {}).get(profile)
            if conf:
                self.teams[team] = conf.get("fleet", self.teams[team])
                self.team_names[team] = conf.get("team_name", self.team_names[team])
                self.normalize_teams()
        except Exception:
            pass

    def save_last_config(self):
        cfg = self.generate_config()
        global _CACHED_CONFIG
        _CACHED_CONFIG = cfg
        try:
            with open(SAVES_FILE, "r") as f:
                saves = json.load(f)
        except Exception:
            saves = {}
        saves["last_config"] = cfg
        try:
            with open(SAVES_FILE, "w") as f:
                json.dump(saves, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save last config: {e}")
            return False

class PauseMenu:
    def __init__(self, screen, clock):
        self.screen = screen
        self.clock = clock
        self.font_title = pygame.font.SysFont("Arial", 48)
        self.font_menu = pygame.font.SysFont("Arial", 36)
        self.font_small = pygame.font.SysFont("Arial", 24)
        self.options = ["Resume", "Main Menu", "Quit"]
        self.selected = 0
        self.done = False
        self.next_state = None
        self.super_menu = None

    def set_super_menu(self, super_menu):
        self.super_menu = super_menu

    def reset(self):
        self.selected = 0
        self.done = False
        self.next_state = None

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            if self.super_menu is not None:
                self.super_menu.save_last_config()
            self.done = True
            self.next_state = "QUIT"
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.done = True
                self.next_state = "RESUME"
            elif event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                self.done = True
                if self.selected == 0:
                    self.next_state = "RESUME"
                elif self.selected == 1:
                    self.next_state = "MENU"
                elif self.selected == 2:
                    if self.super_menu is not None:
                        self.super_menu.save_last_config()
                    self.next_state = "QUIT"

    def draw(self):
        self.screen.fill(BLACK)
        title_surf = self.font_title.render("Paused", True, YELLOW)
        self.screen.blit(title_surf, (SCREEN_W // 2 - title_surf.get_width() // 2, 100))

        for i, option in enumerate(self.options):
            color = YELLOW if i == self.selected else WHITE
            border_color = YELLOW if i == self.selected else GRAY
            border_width = 2 if i == self.selected else 1

            text_surf = self.font_menu.render(option, True, color)
            x = SCREEN_W // 2 - text_surf.get_width() // 2
            y = SCREEN_H // 2 + i * 60
            rect = pygame.Rect(x - 10, y - 10, text_surf.get_width() + 20, text_surf.get_height() + 20)
            pygame.draw.rect(self.screen, border_color, rect, border_width)
            self.screen.blit(text_surf, (x, y))

        instr = "Use UP/DOWN to select, ENTER to confirm"
        self.screen.blit(self.font_small.render(instr, True, WHITE), (10, SCREEN_H - 30))

    def update(self, dt):
        pass

    def display(self):
        self.reset()
        while not self.done:
            for event in pygame.event.get():
                self.handle_event(event)
            self.draw()
            pygame.display.flip()
            self.clock.tick(30)
        return self.next_state

def fast_load_menu(screen, clock):
    menu = SuperMeleeMenu(screen, clock)
    menu.reset()
    return menu.generate_config()
