# project/entities/planet.py
# Обновлён 27.05.2025: удалена визуализация (метод draw) — теперь класс чисто модельный

class Planet:
    def __init__(self, x, y, radius, color):
        self.x = float(x)
        self.y = float(y)
        self.radius = float(radius)
        self.color = color
