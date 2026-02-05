# project/entities/forward_shot.py
# FIXED 2025-08-12: исправлена сигнатура вызова базового Projectile
# Причина: ранее вместо числовых (damage, radius) в Projectile попадали (owner, game_time),
# из-за чего:
#   1) урон становился объектом-владельцем (ошибка логики в столкновениях);
#   2) радиус становился равным game_time и рос от выстрела к выстрелу (желтая заглушка увеличивалась);
#   3) для корректной отрисовки в renderer теперь достаточно иметь owner и вектор скорости.
# Теперь ForwardShot корректно передает damage и фиксированный radius в Projectile,
# owner хранится отдельно и используется renderer'ом для выбора набора кадров.
#
# Дополнительно: убран getattr(self, "radius", 2) — радиус задается явно.

import math
from project.entities.projectile import Projectile

class ForwardShot(Projectile):
    """
    Прямолинейный снаряд короткой жизни.
    Летит по курсу корабля на момент выстрела (не наследует скорость корабля),
    двигается с постоянной скоростью, исчезает по истечении времени жизни,
    при столкновении наносит фиксированный урон.
    """
    def __init__(self, x, y, angle, speed, damage, lifetime, owner, game_time, radius: float = 4.0):
        # Рассчитываем скорость по углу носа корабля
        rad = math.radians(angle)
        vx = math.sin(rad) * speed
        vy = -math.cos(rad) * speed

        # ВАЖНО: передаем именно damage и radius, а НЕ owner/game_time
        super().__init__(x, y, vx, vy, damage=damage, radius=radius)

        # Метаданные и поведение
        self.owner = owner            # нужен рендереру для выбора набора кадров (по классу владельца)
        self.angle = angle
        self.lifetime = float(lifetime)
        self.age = 0.0
        # game_time можно сохранить при необходимости для аналитики/эффектов, но сейчас не используется

    def update(self, dt: float):
        # Базовое движение + wrap-around
        super().update(dt)
        # Тикаем возраст и гасим по истечении жизни
        self.age += dt
        if self.age >= self.lifetime:
            self.active = False
