import math
from project.ships.base_ship import BaseShip
from project.entities.mine import Mine, Plasmoid

class ShipB(BaseShip):
    def __init__(self, x, y, color):
        super().__init__(x, y, color)
        self.name = "KOHR-AH MARAUDER"
        self.max_crew = 42
        self.crew = 42
        self.max_energy = 42
        self.energy = 42
        self.energy_regeneration = 1
        self.energy_wait = 4 / 60.0
        self.energy_timer = self.energy_wait

        self.weapon_energy_cost = 6
        self.weapon_wait = 6 / 60.0
        self.weapon_timer = 0

        self.special_energy_cost = 21
        self.special_wait = 9 / 60.0
        self.special_timer = 0

        self.max_thrust = 70.0
        self.thrust_increment = 3.0
        self.thrust_wait = 11 / 60.0
        self.turn_speed = 90.0

        self.deployed_mines = []  # Фиксированные мины
        self.current_mine = None  # Мина в режиме запуска

        self.cost = self.max_crew  # Стоимость корабля

    def start_mine_launch(self, enemy, game_time):
        if self.current_mine is None and self.weapon_timer <= 0 and self.energy >= self.weapon_energy_cost:
            self.energy -= self.weapon_energy_cost
            self.weapon_timer = self.weapon_wait
            rad = math.radians(self.angle)
            front_x = self.x + self.radius * math.sin(rad)
            front_y = self.y - self.radius * math.cos(rad)
            mine_vx = self.vx + 150 * math.sin(rad)
            mine_vy = self.vy - 150 * math.cos(rad)
            mine = Mine(front_x, front_y, mine_vx, mine_vy, enemy, game_time, launching=True)
            mine.owner = self
            self.current_mine = mine
            return mine
        return None

    def release_mine(self):
        if self.current_mine:
            self.current_mine.vx = 0
            self.current_mine.vy = 0
            self.current_mine.launching = False
            self.deployed_mines.append(self.current_mine)
            if len(self.deployed_mines) > 8:
                oldest = self.deployed_mines.pop(0)
                oldest.active = False
            released = self.current_mine
            self.current_mine = None
            return released
        return None

    def fire_primary(self, enemy, game_time):
        # Основное оружие: запуск мины
        return self.start_mine_launch(enemy, game_time)

    def fire_secondary(self, targets, game_time):
        # Вторичное оружие: создание плазмоидного кольца
        if self.special_timer > 0 or self.energy < self.special_energy_cost:
            return []
        self.energy -= self.special_energy_cost
        self.special_timer = self.special_wait
        ring_start_time = game_time
        plasmoids = []
        for i in range(16):
            angle_deg = i * 22.5
            rad = math.radians(angle_deg)
            p = Plasmoid(rad, ring_start_time, orbit_speed=50.0, lifetime=1.0)
            p.owner = self
            plasmoids.append(p)
        return plasmoids

    def update(self, dt):
        super().update(dt)
        if self.current_mine and not self.current_mine.active:
            self.current_mine = None
