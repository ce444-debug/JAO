import math
import pygame
from project.ships.base_ship import BaseShip
from project.config import FIELD_W, FIELD_H
from project.model.utils import wrap_delta, world_to_screen

class ShipA(BaseShip):
    def __init__(self, x, y, color):
        super().__init__(x, y, color)
        self.name = "Earthling Cruiser"
        self.max_crew = 18
        self.crew = 18
        self.max_energy = 18
        self.energy = 18
        self.energy_regeneration = 1
        self.energy_wait = 8 / 60.0
        self.energy_timer = self.energy_wait

        self.weapon_energy_cost = 9
        self.weapon_wait = 10 / 60.0
        self.weapon_timer = 0

        self.special_energy_cost = 4
        self.special_wait = 9 / 60.0
        self.special_timer = 0

        self.max_thrust = 70.0
        self.thrust_increment = 4.0
        self.thrust_wait = 11 / 60.0
        self.turn_speed = 180.0

        self.cost = self.max_crew

    def fire_primary(self, enemy, game_time):
        if self.weapon_timer <= 0 and self.energy >= self.weapon_energy_cost:
            self.energy -= self.weapon_energy_cost
            self.weapon_timer = self.weapon_wait

            # Нос корабля = (sin(a), -cos(a))
            rad = math.radians(self.angle)
            front_x = self.x + self.radius * math.sin(rad)
            front_y = self.y - self.radius * math.cos(rad)
            missile_vx = self.vx + 50 * math.sin(rad)
            missile_vy = self.vy - 50 * math.cos(rad)

            from project.entities.missile import Missile

            # ШИРОКАЯ ДУГА + дольше живёт (скорости — как в UQM: 40→80, +4/tick)
            missile = Missile(
                front_x, front_y,
                missile_vx, missile_vy,
                enemy, game_time, self.angle,
                profile="UQM",           # UQM скорости/ускорение
                straight_flight_sec=0.10,# каноничная стартовая задержка
                turn_delay_sec=0.10,     # реже корректирует → шире дуга
                turn_step_deg=7.5,       # меньший шаг поворота → шире дуга
                lifetime_sec=7.0         # ↑ жизнь (было 3.0). Поставь 4.5–5.0, если нужно ещё дольше
            )
            missile.owner = self
            return missile

        return None

    def fire_secondary(self, targets, game_time):
        laser_range = self.radius * 2.2 * 2
        valid_targets = []
        for target in targets:
            dx = wrap_delta(self.x, target.x, FIELD_W)
            dy = wrap_delta(self.y, target.y, FIELD_H)
            distance = math.hypot(dx, dy)
            effective_distance = distance - getattr(target, 'radius', 0)
            if effective_distance <= laser_range:
                valid_targets.append(target)

        if not valid_targets or self.special_timer > 0 or self.energy < self.special_energy_cost:
            return None

        self.energy -= self.special_energy_cost
        self.special_timer = self.special_wait

        for target in valid_targets:
            dx = target.x - self.x
            dy = target.y - self.y
            d = math.hypot(dx, dy)
            if d != 0:
                impact_x = target.x - (dx / d) * target.radius
                impact_y = target.y - (dy / d) * target.radius
            else:
                impact_x, impact_y = target.x, target.y
            self.active_lasers.append((impact_x, impact_y, 0.1))

            if hasattr(target, 'launch_time'):
                if target.launch_time < game_time:
                    target.active = False
            else:
                target.take_damage(1)

    def render(self, screen, cam, zoom):
        for (tx, ty, t) in self.active_lasers:
            if t > 0:
                start_pos = world_to_screen(self.x, self.y, cam.x, cam.y, zoom)
                end_pos = world_to_screen(tx, ty, cam.x, cam.y, zoom)
                pygame.draw.line(screen, (255, 0, 0), start_pos, end_pos, 2)
