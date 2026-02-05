# project/entities/effect.py
# Эффекты попадания/гибели. Совместимо с UQM-подобными .ani.
from __future__ import annotations

class Effect:
    __slots__ = ("key", "ship_key", "x", "y", "frame_time", "age", "active")
    def __init__(self, key: str, ship_key: str, x: float, y: float, frame_time: float):
        self.key = key                # 'blast' | 'boom'
        self.ship_key = ship_key      # ключ ассетов корабля или 'default'
        self.x = float(x)
        self.y = float(y)
        self.frame_time = float(frame_time)
        self.age = 0.0
        self.active = True

    def update(self, dt: float) -> None:
        self.age += dt   # выключение делает renderer (он знает число кадров набора)

class HitEffect(Effect):
    __slots__ = ("group", "use_offsets", "angle")
    def __init__(
        self,
        ship_key: str,
        group: int,
        x: float,
        y: float,
        frame_time: float = 0.05,
        *,
        use_offsets: bool = False,
        angle: float | None = None,
    ):
        super().__init__("blast", ship_key, x, y, frame_time)
        self.group = int(group)               # 0..3 — четверти корпуса
        self.use_offsets = bool(use_offsets)  # учитывать ли dx,dy из .ani
        self.angle = angle                    # поворот вспышки по курсу пули (опц.)

class DeathEffect(Effect):
    __slots__ = ("loops",)
    def __init__(self, ship_key: str, x: float, y: float, frame_time: float = 0.07, *, loops: int = 3):
        super().__init__("boom", ship_key, x, y, frame_time)
        self.loops = max(1, int(loops))       # сколько циклов крутить boom
