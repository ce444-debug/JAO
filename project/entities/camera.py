from project.config import FIELD_W, FIELD_H
from project.model.utils import wrap_midpoint

class Camera:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def update_center_on_two_ships(self, sA, sB):
        mx, my = wrap_midpoint(sA.x, sA.y, sB.x, sB.y)
        self.x = mx % FIELD_W
        self.y = my % FIELD_H
