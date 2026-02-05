import math
import random
from project.config import DISCRETE_ROTATION, ROTATION_STEP_DEGREES

class AIController:
    def __init__(self, ship, difficulty="Medium"):
        """
        Базовый AI-контроллер с общими методами навигации, уклонения и стрельбы.
        difficulty: "Easy", "Medium" или "Hard"
        """
        self.ship = ship
        self.difficulty = difficulty
        if self.difficulty == "Easy":
            self.reaction_time = 0.5
            self.dodge_chance = 0.3
        elif self.difficulty == "Medium":
            self.reaction_time = 0.3
            self.dodge_chance = 0.6
        else:
            self.reaction_time = 0.1
            self.dodge_chance = 1.0
        self._decision_timer = 0.0

    def update(self, dt, enemy, obstacles, projectiles):
        self._decision_timer += dt
        if self._decision_timer < self.reaction_time:
            return
        self._decision_timer = 0.0

        avoid_direction = self.avoid_obstacles(obstacles)
        target_angle, thrust = self.determine_movement(enemy)
        if avoid_direction is not None:
            target_angle = avoid_direction
            thrust = True
        if self.check_dodge_needed(projectiles):
            dodge_angle = (self.ship.angle + (90 if random.random() < 0.5 else -90)) % 360
            target_angle = dodge_angle
            thrust = True

        self.turn_towards(target_angle, dt)
        if thrust:
            self.ship.accelerate()
        self.fire_weapons(enemy)

    def determine_movement(self, enemy):
        raise NotImplementedError

    def fire_weapons(self, enemy):
        raise NotImplementedError

    def avoid_obstacles(self, obstacles):
        for obs in obstacles:
            dx = obs.x - self.ship.x
            dy = obs.y - self.ship.y
            safe_dist = (obs.radius + getattr(self.ship, "radius", 0) + 50) ** 2
            if dx * dx + dy * dy < safe_dist:
                angle_to_obs = math.degrees(math.atan2(dy, dx))
                avoid_angle = (angle_to_obs + 90) % 360
                return avoid_angle
        return None

    def check_dodge_needed(self, projectiles):
        for proj in projectiles:
            dx = self.ship.x - proj.x
            dy = self.ship.y - proj.y
            if dx * dx + dy * dy < 100 ** 2:
                proj_angle = math.degrees(math.atan2(proj.vy, proj.vx))
                angle_to_ship = math.degrees(math.atan2(dy, dx))
                angle_diff = abs((proj_angle - angle_to_ship + 180) % 360 - 180)
                if angle_diff < 30 and random.random() < self.dodge_chance:
                    return True
        return False

    def turn_towards(self, target_angle, dt):
        if DISCRETE_ROTATION and hasattr(self.ship, 'rotate_left'):
            diff = ((target_angle - self.ship.angle + 180) % 360) - 180
            # Snap if within half step
            if abs(diff) < ROTATION_STEP_DEGREES / 2:
                nearest = round(target_angle / ROTATION_STEP_DEGREES) % 16
                self.ship.angle = (nearest * ROTATION_STEP_DEGREES) % 360
            else:
                if diff > 0:
                    self.ship.rotate_right(dt)
                else:
                    self.ship.rotate_left(dt)
        else:
            turn_rate = getattr(self.ship, 'turn_speed', 180)
            diff = ((target_angle - self.ship.angle + 180) % 360) - 180
            if abs(diff) < turn_rate * dt:
                self.ship.angle = target_angle % 360
            else:
                self.ship.angle += math.copysign(turn_rate * dt, diff)
                self.ship.angle %= 360

class EarthlingAIController(AIController):
    def determine_movement(self, enemy):
        dx = enemy.x - self.ship.x
        dy = enemy.y - self.ship.y
        angle_to_enemy = math.degrees(math.atan2(dy, dx))
        return angle_to_enemy, True

    def fire_weapons(self, enemy):
        dx = enemy.x - self.ship.x
        dy = enemy.y - self.ship.y
        angle_to_enemy = math.degrees(math.atan2(dy, dx))
        angle_diff = abs((angle_to_enemy - self.ship.angle + 180) % 360 - 180)
        missile_range = 700.0
        distance = math.hypot(dx, dy)
        if angle_diff < 30 and distance <= missile_range:
            self.ship.fire_primary(enemy, 0)

class KohrAhAIController(AIController):
    def __init__(self, ship, difficulty="Medium"):
        super().__init__(ship, difficulty)
        self.mine_cooldown = 0.0

    def determine_movement(self, enemy):
        dx = enemy.x - self.ship.x
        dy = enemy.y - self.ship.y
        target_angle = math.degrees(math.atan2(dy, dx))
        return target_angle, True

    def fire_weapons(self, enemy):
        self.ship.fire_primary(enemy, 0)
        dx = enemy.x - self.ship.x
        dy = enemy.y - self.ship.y
        distance = math.hypot(dx, dy)
        if distance < 300 and self.mine_cooldown <= 0:
            self.ship.fire_secondary([enemy], 0)
            self.mine_cooldown = {'Hard':0.8, 'Medium':1.0, 'Easy':1.5}[self.difficulty]
        if self.mine_cooldown > 0:
            self.mine_cooldown -= self.reaction_time
