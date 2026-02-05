# project/entities/missile.py
# UQM-совместимая ракета: UQM-геометрия, дискретное наведение, профили UQM / UQM_PLUS
# - храним угол в UQM (0°=вверх, + по часовой)
# - desired берём как atan2(-dy, dx) (экранная Y вниз), переводим в UQM
# - движение = (sin(a), -cos(a))
# - кадр = frame_index по UQM-углу (16 направлений)
# - дуга: ограниченный поворот (turn_step_deg) раз в turn_delay_sec после прямого straight_flight_sec
# - есть нормализация dt (мс -> с)

import math
from project.config import FIELD_W, FIELD_H
from project.model.utils import wrap_position, wrap_delta
from project.entities.projectile import Projectile

TICKS_PER_SEC = 60.0

# --- Профили (UQM-канон и «чуть быстрее/дальше») ---
PROFILES = {
    "UQM": dict(
        straight_flight_sec = 6.0 / TICKS_PER_SEC,   # 0.1 s
        turn_delay_sec      = 3.0 / TICKS_PER_SEC,   # 0.05 s
        turn_step_deg       = 22.5,                  # 16 направлений
        lifetime_sec        = 8.0,                   # ≈180 тиков
        accel_per_tick      = 6.0,                   # +4/tick
        initial_speed       = 80.0,
        max_speed           = 160.0
    ),
    "UQM_PLUS": dict(                              # «чуть быстрее и дальше»
        straight_flight_sec = 6.0 / TICKS_PER_SEC,  # сохраняем UQM-тайминги поведения
        turn_delay_sec      = 3.0 / TICKS_PER_SEC,
        turn_step_deg       = 22.5,
        lifetime_sec        = 4.5,                   # дольше летит → почти до края
        accel_per_tick      = 5.0,                   # +5/tick (=300 u/s²)
        initial_speed       = 60.0,                  # чуть быстрее старт
        max_speed           = 120.0                  # быстрее потолок
    ),
}

def _normalize_angle_rad(a: float) -> float:
    return (a + math.pi) % (2.0 * math.pi) - math.pi

def _dt_sec(dt: float) -> float:
    # если пришло ~16-33 (мс), переводим в секунды
    return dt / 1000.0 if dt > 0.5 else dt

def angle_math_to_uqm(angle_math_rad: float) -> float:
    # math/pygame: 0°=вправо (ccw) -> UQM: 0°=вверх (cw)
    return math.radians(90.0) - angle_math_rad

def angle_to_facing_uqm(angle_uqm_rad: float) -> int:
    deg = (math.degrees(angle_uqm_rad)) % 360.0
    return int((deg + 11.25) // 22.5) % 16


class Missile(Projectile):
    def __init__(
        self,
        x, y,
        vx, vy,
        target,
        launch_time,
        ship_angle=0.0,
        *,
        # можно указать профиль заранее (по умолчанию — «канон» UQM)
        profile: str = "UQM",
        # либо переопределить отдельные поля вручную (приоритет над профилем)
        straight_flight_sec: float | None = None,
        turn_delay_sec: float | None = None,
        turn_step_deg: float | None = None,
        lifetime_sec: float | None = None,
        accel_per_tick: float | None = None,
        initial_speed: float | None = None,
        max_speed: float | None = None,
    ):
        super().__init__(x, y, vx, vy, damage=4, radius=5)
        self.target = target
        self.launch_time = launch_time

        # 1) старт по курсу корабля (UQM-угол)
        self.facing = math.radians(ship_angle)
        self.frame_index = angle_to_facing_uqm(self.facing)

        # 2) загрузка профиля
        p = PROFILES.get(profile, PROFILES["UQM"]).copy()
        if straight_flight_sec is not None: p["straight_flight_sec"] = float(straight_flight_sec)
        if turn_delay_sec      is not None: p["turn_delay_sec"]      = float(turn_delay_sec)
        if turn_step_deg       is not None: p["turn_step_deg"]       = float(turn_step_deg)
        if lifetime_sec        is not None: p["lifetime_sec"]        = float(lifetime_sec)
        if accel_per_tick      is not None: p["accel_per_tick"]      = float(accel_per_tick)
        if initial_speed       is not None: p["initial_speed"]       = float(initial_speed)
        if max_speed           is not None: p["max_speed"]           = float(max_speed)

        # 3) применяем параметры
        self.turn_wait   = p["straight_flight_sec"]
        self.turn_delay  = p["turn_delay_sec"]
        self._turn_step_rad = math.radians(p["turn_step_deg"])
        self.lifetime    = p["lifetime_sec"]
        self.accel       = p["accel_per_tick"] * TICKS_PER_SEC  # u/s²
        self.speed       = p["initial_speed"]
        self.max_speed   = p["max_speed"]

        # служебное
        self.age = 0.0
        self.exploding = False
        self.explosion_age = 0.0
        self.explosion_fps = 14.0

    def update(self, dt_raw: float):
        dt = _dt_sec(dt_raw)

        if self.exploding:
            self.explosion_age += dt
            return

        # lifetime
        self.age += dt
        self.lifetime -= dt
        if self.lifetime <= 0.0 and not self.exploding:
            self.exploding = True
            self.explosion_age = 0.0
            return

        # наведение
        if self.turn_wait > 0.0:
            self.turn_wait -= dt
            if self.turn_wait < 0.0:
                self.turn_wait = 0.0
        else:
            if self.target is not None and getattr(self.target, "active", True):
                dx = wrap_delta(self.x, self.target.x, FIELD_W)
                dy = wrap_delta(self.y, self.target.y, FIELD_H)
                if dx != 0.0 or dy != 0.0:
                    # экранная Y вниз → atan2(-dy, dx)
                    desired_math = math.atan2(-dy, dx)
                    desired_uqm  = angle_math_to_uqm(desired_math)

                    delta = _normalize_angle_rad(desired_uqm - self.facing)

                    # ограниченный поворот (дуга)
                    if delta > 0.0:
                        step = min(delta, self._turn_step_rad)
                    else:
                        step = max(delta, -self._turn_step_rad)

                    self.facing = _normalize_angle_rad(self.facing + step)
                    self.frame_index = angle_to_facing_uqm(self.facing)
                    self.turn_wait = self.turn_delay

        # ускорение и ограничение скорости
        self.speed += self.accel * dt
        if self.speed > self.max_speed:
            self.speed = self.max_speed

        # движение в UQM-геометрии
        self.vx = math.sin(self.facing) * self.speed
        self.vy = -math.cos(self.facing) * self.speed

        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x, self.y = wrap_position(self.x, self.y)
