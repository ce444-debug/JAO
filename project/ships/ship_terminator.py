import math
from project.ships.base_ship import BaseShip
from project.entities.forward_shot import ForwardShot


class ShipTerminator(BaseShip):
    """
    Yehat Terminator.
    Основное оружие: спаренные импульсы (двойной выстрел).

    Изменения 2025-09-16 — Щит как доп. оружие (целочисленная энергия, дискретный дрен):
    - Включение щита требует энергии >= shield_energy_cost; стоимость списывается сразу.
    - Пока удерживаешь и щит активен — энергия убывает целыми шагами (shield_drain_amount)
      с периодом shield_drain_interval (сек).
    - Авто-реактивация при удержании произойдёт только когда снова накопится >= shield_energy_cost
      (и тут же спишется разовая стоимость).
    - Энергия в этом классе принудительно ведётся как ЦЕЛОЕ число (0..max_energy).
    - Активный щит полностью блокирует урон.
    """

    def __init__(self, x, y, color):
        super().__init__(x, y, color)
        self.name = "YEHAT TERMINATOR"

        # Экипаж
        self.max_crew = 20
        self.crew = 20

        # Энергетика
        self.max_energy = 10
        self.energy = 10  # будем поддерживать целым числом

        # Движение
        self.max_thrust = 80.0
        self.thrust_increment = 10.0

        # Реген энергии (базовый механизм в BaseShip)
        self.energy_regeneration = 1     # за тик регена
        self.energy_wait = 0.15          # период тика регена (сек)

        # Оружие
        self.weapon_energy_cost = 1
        self.weapon_wait = 0.0
        self.weapon_timer = 0.0

        # Очередь
        self.burst_interval = 0.07
        self.burst_timer = 0.0
        self.burst_angle = 0.0
        self.primary_held = False
        self.burst_pending_shots = []

        # Снаряды
        self.weapon_projectile_speed = 650.0
        self.weapon_projectile_damage = 1
        self.weapon_projectile_lifetime = 0.35
        self.weapon_projectile_radius = 4.0

        # ---------- Shield (secondary-style, integer drain) ----------
        self.secondary_held = False
        self.shield_active = False

        # Разовый расход при включении (как у доп. оружия)
        self.shield_energy_cost = 3  # ЦЕЛОЕ

        # Дискретный дрен при удержании
        self.shield_drain_amount = 1           # сколько списываем за тик
        self.shield_drain_interval = 0.10      # как часто (сек)
        self._shield_drain_timer = 0.0         # накопитель времени между тиками

    # ---------- Primary fire ----------
    def fire_primary(self, enemy, game_time):
        self.primary_held = True
        self.burst_angle = self.angle
        self.burst_timer = 0.0
        shots = self._try_fire_double(game_time)
        if shots:
            return shots
        return None

    def release_primary(self):
        self.primary_held = False

    # ---------- Secondary (shield) ----------
    def fire_secondary(self, targets, game_time):
        """
        Удержание + немедленное включение, если хватает энергии на стартовую стоимость.
        """
        self.secondary_held = True
        if not self.shield_active and self.energy >= self.shield_energy_cost:
            self.energy -= self.shield_energy_cost
            self.energy = max(0, min(self.max_energy, int(self.energy)))  # держим целым
            self.shield_active = True
            self._shield_drain_timer = 0.0
        return None

    def release_secondary(self):
        self.secondary_held = False
        if self.shield_active:
            self.shield_active = False
        self._shield_drain_timer = 0.0

    # ---------- Update ----------
    def update(self, dt):
        # Базовая физика + реген из BaseShip
        super().update(dt)

        # Приводим энергию к целому (на случай, если BaseShip накапал дроби)
        self.energy = max(0, min(self.max_energy, int(self.energy)))

        # Оружие — таймеры
        if self.weapon_timer > 0.0:
            self.weapon_timer = max(0.0, self.weapon_timer - dt)
        if self.burst_timer > 0.0:
            self.burst_timer -= dt

        # Очередь при удержании
        if self.primary_held and self.burst_timer <= 0.0:
            shots = self._try_fire_double(game_time=0.0)
            if shots:
                self.burst_pending_shots.extend(shots)
                self.burst_timer += self.burst_interval

        # ---------- Shield logic ----------
        # (ре)включение при удержании только если хватает на стартовую стоимость
        if self.secondary_held and not self.shield_active and self.energy >= self.shield_energy_cost:
            self.energy -= self.shield_energy_cost
            self.energy = max(0, min(self.max_energy, int(self.energy)))
            self.shield_active = True
            self._shield_drain_timer = 0.0

        if self.shield_active:
            # Тикаем таймер дренажа
            self._shield_drain_timer += dt
            while self._shield_drain_timer >= self.shield_drain_interval:
                if self.energy >= self.shield_drain_amount:
                    self.energy -= self.shield_drain_amount
                    self.energy = max(0, min(self.max_energy, int(self.energy)))
                    self._shield_drain_timer -= self.shield_drain_interval
                else:
                    # Энергии не осталось — гасим щит
                    self.shield_active = False
                    self._shield_drain_timer = 0.0
                    break



    # ---------- Damage ----------
    def take_damage(self, amount):
        if self.shield_active:
            return
        super().take_damage(amount)

    # ---------- Firing helpers ----------
    def _try_fire_double(self, game_time):
        total_cost = 2 * self.weapon_energy_cost
        if self.energy < total_cost:
            return None

        self.energy -= total_cost
        self.energy = max(0, min(self.max_energy, int(self.energy)))

        rad = math.radians(self.burst_angle)
        forward_x = math.sin(rad)
        forward_y = -math.cos(rad)
        perp_x = math.cos(rad)
        perp_y = math.sin(rad)

        front_offset = self.radius
        base_x = self.x + forward_x * front_offset
        base_y = self.y + forward_y * front_offset

        left_x = base_x - perp_x * self.radius
        left_y = base_y - perp_y * self.radius
        right_x = base_x + perp_x * self.radius
        right_y = base_y + perp_y * self.radius

        shot_left = ForwardShot(
            left_x, left_y, self.burst_angle,
            speed=self.weapon_projectile_speed,
            damage=self.weapon_projectile_damage,
            lifetime=self.weapon_projectile_lifetime,
            owner=self,
            game_time=game_time,
            radius=self.weapon_projectile_radius
        )
        shot_right = ForwardShot(
            right_x, right_y, self.burst_angle,
            speed=self.weapon_projectile_speed,
            damage=self.weapon_projectile_damage,
            lifetime=self.weapon_projectile_lifetime,
            owner=self,
            game_time=game_time,
            radius=self.weapon_projectile_radius
        )
        return [shot_left, shot_right]
