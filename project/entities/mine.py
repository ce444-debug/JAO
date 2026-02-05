# project/entities/mine.py
# Обновлён 29.05.2025: удалены методы draw — теперь визуализация выполняется в view/renderer.py

import math
from project.model.utils import wrap_position, wrap_delta
from project.entities.projectile import Projectile
from project.config import FIELD_W, FIELD_H

class Mine(Projectile):
    def __init__(self, x, y, vx, vy, target, launch_time, launching=True):
        """
        Наследует Projectile (damage=4, radius=5) и добавляет механику самонаведения после запуска.
        """
        # Наследуем общие поля из Projectile: damage=4, radius=5
        super().__init__(x, y, vx, vy, damage=4, radius=5)
        self.target = target
        self.speed = 200.0         # Базовая скорость для режима homing
        self.homing_strength = 1.0 # Коэффициент корректировки скорости в режиме homing
        self.launch_time = launch_time
        self.launching = launching   # True, пока мина находится в режиме запуска

    def update(self, dt):
        """
        Если минa в фазе запуска (launching=True), двигается по заранее заданному vx, vy.
        После окончания запуска — переходит в поведение homing (если цель активна).
        """
        if self.launching:
            # В режиме запуска мина просто движется по начальной скорости
            self.x += self.vx * dt
            self.y += self.vy * dt
        else:
            # После запуска: режим homing
            if self.target is not None and getattr(self.target, 'active', True):
                dx = wrap_delta(self.x, self.target.x, FIELD_W)
                dy = wrap_delta(self.y, self.target.y, FIELD_H)
                distance = math.hypot(dx, dy)
                tracking_range = 24 * self.radius  # Диапазон отслеживания
                if distance <= tracking_range and distance != 0:
                    desired_vx = self.speed * dx / distance
                    desired_vy = self.speed * dy / distance
                    self.vx += (desired_vx - self.vx) * self.homing_strength * dt
                    self.vy += (desired_vy - self.vy) * self.homing_strength * dt
                else:
                    # Если слишком далеко или цель неактивна — мина останавливается
                    self.vx = 0
                    self.vy = 0
            else:
                self.vx = 0
                self.vy = 0
            self.x += self.vx * dt
            self.y += self.vy * dt

        # Общая логика обёртки по полю
        self.x, self.y = wrap_position(self.x, self.y)

class Plasmoid(Projectile):
    """
    Класс плазмоида, который при рождении образует разрастающееся кольцо (orbit) вокруг владельца.
    После окончания жизни (lifetime) плазмоид исчезает.
    """
    RING_SCALING = 1.5  # Множитель для увеличения радиуса кольца

    def __init__(self, orbit_angle, ring_start_time, orbit_speed=50.0, lifetime=1.0):
        # Изначально позиция и скорость неизвестны, поэтому задаём (0,0), damage=3, radius=4
        super().__init__(0, 0, 0, 0, damage=3, radius=4)
        self.owner = None             # Устанавливается владельцем (ship) при создании
        self.orbit_angle = orbit_angle
        self.ring_start_time = ring_start_time
        self.orbit_speed = orbit_speed
        self.base_radius = 4          # Базовый радиус плазмоида
        self.radius = self.base_radius
        self.lifetime = lifetime

    def update(self, dt, game_time):
        """
        При обновлении уменьшаем lifetime. Если время вышло — деактивируем.
        Иначе расчитываем новое положение (расширяющееся кольцо вокруг owner или прямолинейно).
        """
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.active = False
            return

        orbit_distance = Plasmoid.RING_SCALING * (game_time - self.ring_start_time) * self.orbit_speed
        if self.owner is not None:
            # Движение вокруг владельца по углу orbit_angle
            self.x = self.owner.x + orbit_distance * math.sin(self.orbit_angle)
            self.y = self.owner.y - orbit_distance * math.cos(self.orbit_angle)
        else:
            # Если owner не задан, плазмоид летит прямо по заданной orbit_angle
            self.x += self.orbit_speed * dt * math.sin(self.orbit_angle)
            self.y -= self.orbit_speed * dt * math.cos(self.orbit_angle)

        # Изменяем радиус по мере «расширения кольца»
        self.radius = self.base_radius + orbit_distance / 50.0

        # Обёртка по полю
        self.x, self.y = wrap_position(self.x, self.y)
