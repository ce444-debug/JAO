# project/entities/asteroids.py
# Обновлён 12.07.2025: исправлена логика установки флага destroyed для корректного проигрывания анимации

import random
from project.config import ASTEROID_ROTATION_AXIS
from project.model.utils import wrap_position

class Asteroid:
    def __init__(self, x, y, radius, vx, vy, color):
        self.x = float(x)
        self.y = float(y)
        self.radius = float(radius)
        self.vx = float(vx)
        self.vy = float(vy)
        self.color = color
        self.angle = random.uniform(0, 360)
        self.angular_velocity = ASTEROID_ROTATION_AXIS * random.uniform(50, 180)
        self.max_health = 1
        self.health = self.max_health
        self.active = True

        # Анимация разрушения
        self.is_destroying = False          # если True — проигрываем destroy анимацию
        self.destroy_frame_index = 0        # индекс кадра разрушения
        self.destroyed = False              # астероид полностью уничтожен (удаляется)

    def update(self, dt):
        if self.is_destroying:
            # увеличиваем индекс кадра анимации
            self.destroy_frame_index += 1
            print(f"[Asteroid] destroying... frame {self.destroy_frame_index}")
            # Проверяем, следует ли завершить анимацию
            if self.destroy_frame_index >= 4:  # Кол-во кадров разрушения
                print(f"[Asteroid] fully destroyed at ({self.x:.1f}, {self.y:.1f})")
                # Устанавливаем плитку полностью уничтоженной только после проигрывания всех кадров
                self.destroyed = True  # CHANGED: перенос установки destroyed внутрь условия
            return

        # Обычное поведение астероида
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x, self.y = wrap_position(self.x, self.y)
        self.angle = (self.angle + self.angular_velocity * dt) % 360

    def take_damage(self, amount):
        if not self.is_destroying and not self.destroyed:
            self.health -= amount
            if self.health <= 0:
                self.start_destruction()

    def start_destruction(self):
        print(f"[Asteroid] start_destruction at ({self.x:.1f}, {self.y:.1f})")
        self.is_destroying = True
        self.destroy_frame_index = 0
        self.active = False  # больше не взаимодействует с миром
