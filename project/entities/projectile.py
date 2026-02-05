# project/entities/projectile.py
# Обновлён 27.05.2025: удалён метод draw — теперь визуализацию выполняет view/renderer.py

import math
from project.config import FIELD_W, FIELD_H
from project.model.utils import wrap_position, wrap_delta

class Projectile:
    def __init__(self, x, y, vx, vy, damage, radius):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.damage = damage
        self.radius = radius
        self.active = True

    def update(self, dt):
        # Базовая логика обновления: простое движение с учетом инерции
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x, self.y = wrap_position(self.x, self.y)

    # Раньше здесь был метод draw(), теперь перенёс его в view/renderer.py

    def on_hit(self, target):
        # При попадании наносим урон цели и деактивируем снаряд
        target.take_damage(self.damage)
        self.active = False
