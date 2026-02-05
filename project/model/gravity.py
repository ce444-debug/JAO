# project/model/gravity.py
import math
from project.config import GRAVITY_RANGE, GRAVITY_STRENGTH, FIELD_W, FIELD_H, GRAVITY_MODEL
from project.model.utils import wrap_delta, wrap_position

def apply_gravity(ship, planet, dt):
    dx = wrap_delta(ship.x, planet.x, FIELD_W)
    dy = wrap_delta(ship.y, planet.y, FIELD_H)
    distance = math.hypot(dx, dy)
    if distance < GRAVITY_RANGE and distance != 0:
        nx = dx / distance
        ny = dy / distance
        if GRAVITY_MODEL == "inverse_square":
            # Новый подход: закон обратного квадрата.
            # Используем epsilon для предотвращения слишком сильного ускорения при малых расстояниях.
            epsilon = 1.0
            accel = GRAVITY_STRENGTH / ((distance + epsilon) ** 2)
        else:
            # Старая модель: линейное уменьшение силы с расстоянием.
            factor = (1 - distance / GRAVITY_RANGE)
            accel = GRAVITY_STRENGTH * factor * 3
        ship.vx += nx * accel * dt
        ship.vy += ny * accel * dt
        # --- Изменено: устанавливаем флаг гравитационного манёвра,
        # что позволяет кораблю превышать max_thrust в этом кадре ---
        ship.in_gravity_field = True
        # --- Конец изменений ---
