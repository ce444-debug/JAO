# project/model/utils.py
import math
import random
from project.config import FIELD_W, FIELD_H, GAME_SCREEN_W, SCREEN_H

def spawn_ship():
    margin = 15  # чтобы корабль полностью был внутри поля
    x = random.uniform(margin, FIELD_W - margin)
    y = random.uniform(margin, FIELD_H - margin)
    return (x, y)

def wrap_coord(coord, max_val):
    return coord % max_val

def wrap_position(x, y):
    return (x % FIELD_W, y % FIELD_H)

def wrap_delta(origin, target, max_val):
    d = target - origin
    if d > max_val / 2:
        d -= max_val
    elif d < -max_val / 2:
        d += max_val
    return d

def wrap_midpoint(xA, yA, xB, yB):
    dx = wrap_delta(xA, xB, FIELD_W)
    dy = wrap_delta(yA, yB, FIELD_H)
    midx = xA + 0.5 * dx
    midy = yA + 0.5 * dy
    return wrap_position(midx, midy)

def world_to_screen(obj_x, obj_y, cam_x, cam_y, zoom):
    dx = wrap_delta(cam_x, obj_x, FIELD_W)
    dy = wrap_delta(cam_y, obj_y, FIELD_H)
    from project.config import GAME_SCREEN_W, SCREEN_H
    sx = (GAME_SCREEN_W / 2) + dx * zoom
    sy = (SCREEN_H / 2) + dy * zoom
    return (int(sx), int(sy))
