import math
import random
from project.config import DISCRETE_ROTATION, ROTATION_STEP_DEGREES
from project.config import FIELD_W, FIELD_H
from project.config import SPAWN_EFFECT_DURATION, SPAWN_PHANTOM_COUNT, SPAWN_PHANTOM_STEP
from project.config import RANDOM_SPAWN_ORIENTATION
from project.model.utils import wrap_position, wrap_delta


class BaseShip:
    next_id = 1

    def __init__(self, x, y, color):
        self.id = BaseShip.next_id
        BaseShip.next_id += 1

        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.color = color
        self.radius = 15
        self.angle = 0.0  # 0° – направлен вверх

        # Ensure renderer can resolve frames even if class-name mapping differs
        if not hasattr(self, "asset_key") or self.asset_key is None:
            cname = self.__class__.__name__.lower()
            if "terminator" in cname:
                self.asset_key = "yehat"
            elif "shipa" in cname or "cruiser" in cname:
                self.asset_key = "cruiser"
            elif "shipb" in cname or "kohr" in cname:
                self.asset_key = "kohr_ah"
            else:
                # fallback — let renderer choose first loaded
                self.asset_key = None

        # ---------- RANDOM ORIENTATION ON SPAWN ----------
        if RANDOM_SPAWN_ORIENTATION:
            if DISCRETE_ROTATION:
                steps = int(round(360.0 / ROTATION_STEP_DEGREES))
                self.angle = random.randint(0, max(1, steps) - 1) * ROTATION_STEP_DEGREES
            else:
                self.angle = random.uniform(0.0, 360.0)

        # ---------- UQM SPAWN STATE ----------
        self.is_spawning = True
        self.spawn_timer = float(SPAWN_EFFECT_DURATION)  # общая длительность эффекта

        # Вектор «назад от носа» — по нему раскладываются фантомы
        self.warp_entry_dir = (0.0, 1.0)  # будет пересчитан из self.angle
        self._recalc_warp_entry_dir()

        # Предвычисленные смещения (дальние фантомы первыми)
        self.spawn_phantom_offsets = [SPAWN_PHANTOM_STEP * i for i in range(SPAWN_PHANTOM_COUNT, 0, -1)]

        self.active_lasers = []

        self.name = "BaseShip"
        self.max_crew = 10
        self.crew = 10
        self.max_energy = 10
        self.energy = 10
        self.energy_regeneration = 1
        self.energy_wait = 1.0
        self.energy_timer = self.energy_wait

        self.weapon_energy_cost = 1
        self.weapon_wait = 1.0
        self.weapon_timer = 0

        self.special_energy_cost = 1
        self.special_wait = 1.0
        self.special_timer = 0

        self.max_thrust = 20.0
        self.thrust_increment = 3.0
        self.thrust_wait = 0.1
        self.turn_speed = 90.0

        self.in_gravity_field = False
        self.accelerating = False
        self.dead = False

        # Таймер накопления для дискретного поворота
        self.turn_timer = 0.0

    # ----- Эффект появления: служебные методы -----
    def _recalc_warp_entry_dir(self):
        """Пересчитать единичный вектор «назад от носа» (для цепочки фантомов).
        Нос корабля соответствует направлению (sin(a), -cos(a)),
        поэтому «назад» — (-sin(a), +cos(a)).
        """
        rad = math.radians(self.angle)
        back_x = -math.sin(rad)
        back_y = math.cos(rad)
        # нормализация (на всякий случай)
        length = math.hypot(back_x, back_y) or 1.0
        self.warp_entry_dir = (back_x / length, back_y / length)

    def restart_spawn_effect(self, *, keep_angle=False):
        """Подготовить корабль к новому появлению (respawn).
        Если keep_angle=False и включён RANDOM_SPAWN_ORIENTATION — выбрать новый случайный угол.
        """
        if not keep_angle and RANDOM_SPAWN_ORIENTATION:
            if DISCRETE_ROTATION:
                steps = int(round(360.0 / ROTATION_STEP_DEGREES))
                self.angle = random.randint(0, max(1, steps) - 1) * ROTATION_STEP_DEGREES
            else:
                self.angle = random.uniform(0.0, 360.0)

        self.is_spawning = True
        self.spawn_timer = float(SPAWN_EFFECT_DURATION)
        self._recalc_warp_entry_dir()

        # Пересоздаём offsets на случай изменения конфига
        self.spawn_phantom_offsets = [SPAWN_PHANTOM_STEP * i for i in range(SPAWN_PHANTOM_COUNT, 0, -1)]

        # Блокируем ускорение на время спауна
        self.accelerating = False

    @property
    def spawn_active(self) -> bool:
        return self.is_spawning

    def update(self, dt):
        # --- Эффект появления: обновление таймера (первым делом) ---
        if self.is_spawning:
            # Cap decrement to avoid huge first-frame dt skipping the effect entirely
            self.spawn_timer = max(0.0, self.spawn_timer - min(dt, 0.05))
            if self.spawn_timer == 0.0:
                self.is_spawning = False

        # Перемещение и ограничение поля
        # Во время спауна корабль не двигается
        if not self.is_spawning:
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.x, self.y = wrap_position(self.x, self.y)
        else:
            # Во время появления игнорируем накопленное ускорение
            self.accelerating = False

        # Восстановление энергии
        self.energy_timer -= dt
        if self.energy_timer <= 0:
            if self.energy < self.max_energy:
                self.energy = min(self.max_energy, self.energy + self.energy_regeneration)
            self.energy_timer = self.energy_wait

        # Таймеры оружия
        if self.weapon_timer > 0:
            self.weapon_timer -= dt
        if self.special_timer > 0:
            self.special_timer -= dt

        # Обновление активных лазеров
        new_lasers = []
        for (tx, ty, t) in self.active_lasers:
            t -= dt
            if t > 0:
                new_lasers.append((tx, ty, t))
        self.active_lasers = new_lasers

        # Гладкое поворачивание скорости и ускорение
        if self.accelerating and not self.is_spawning:
            # 1) Повернуть вектор скорости к курсу
            speed = math.hypot(self.vx, self.vy)
            if speed > 0.0:
                vel_angle = math.degrees(math.atan2(self.vx, -self.vy))
                angle_diff = ((self.angle - vel_angle + 180.0) % 360.0) - 180.0
                max_turn = self.turn_speed * dt
                turn_amount = math.copysign(min(abs(angle_diff), max_turn), angle_diff)
                new_vel_angle = vel_angle + turn_amount
                rad = math.radians(new_vel_angle)
                self.vx = speed * math.sin(rad)
                self.vy = -math.cos(rad) * speed

            # 2) Добавить ускорение по курсу
            rad0 = math.radians(self.angle)
            self.vx += self.thrust_increment * math.sin(rad0)
            self.vy += self.thrust_increment * -math.cos(rad0)

            # 3) Ограничить максимальную скорость
            new_speed = math.hypot(self.vx, self.vy)
            if new_speed > self.max_thrust and not self.in_gravity_field:
                scale = self.max_thrust / new_speed
                self.vx *= scale
                self.vy *= scale

        # Сброс флага ускорения
        self.accelerating = False

    def take_damage(self, amount):
        self.crew -= amount
        if self.crew <= 0:
            print(f"{self.name} (ID {self.id}) destroyed!")
            self.dead = True

    @property
    def active(self):
        return not self.dead

    def fire_primary(self, enemy, game_time):
        raise NotImplementedError

    def fire_secondary(self, targets, game_time):
        raise NotImplementedError

    def accelerate(self):
        # Во время спауна ускорение игнорируется
        if self.is_spawning:
            return
        current_speed = math.hypot(self.vx, self.vy)
        if current_speed > self.max_thrust and not self.in_gravity_field:
            return
        self.accelerating = True

    def rotate_left(self, dt):
        # Во время появления не вращаем корабль
        if self.is_spawning:
            return
        if DISCRETE_ROTATION:
            self.turn_timer += dt
            step_time = ROTATION_STEP_DEGREES / self.turn_speed
            while self.turn_timer >= step_time:
                self.angle = (self.angle - ROTATION_STEP_DEGREES) % 360.0
                self.turn_timer -= step_time
        else:
            self.angle = (self.angle - self.turn_speed * dt) % 360.0
        self._recalc_warp_entry_dir()

    def rotate_right(self, dt):
        # Во время появления не вращаем корабль
        if self.is_spawning:
            return
        if DISCRETE_ROTATION:
            self.turn_timer += dt
            step_time = ROTATION_STEP_DEGREES / self.turn_speed
            while self.turn_timer >= step_time:
                self.angle = (self.angle + ROTATION_STEP_DEGREES) % 360.0
                self.turn_timer -= step_time
        else:
            self.angle = (self.angle + self.turn_speed * dt) % 360.0
        self._recalc_warp_entry_dir()
